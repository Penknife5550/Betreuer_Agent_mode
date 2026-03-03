"""
Views for the contracts app.

Covers: Betreuer registration (token + public), registration link management,
betreuer list/detail/review/activate, Koordinator approval, and HTMX endpoints.

V2 Changes:
- Hash-based duplicate detection during registration.
- Betreuer sets own password during registration.
- New Koordinator approval step (pending_approval -> approved).
- start_date left null until Koordinator approval.
- HTMX hash-check endpoint for live duplicate detection.
"""

import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.accounts.models import UserProfile
from apps.contracts.forms import BetreuerRegistrationForm, RegistrationLinkForm
from apps.contracts.models import BetreuerProfile, Contract, RegistrationLink
from apps.documents.models import Document, DocumentRequirement
from apps.notifications.services import notify_betreuer_registered
from apps.rates.models import ActivityType, HourlyRate
from apps.schools.models import Foerderprogramm, School, SchoolYear

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class KoordinatorOrAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin that restricts access to Koordinator and Admin users."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        # Django superusers always have full access
        if user.is_superuser:
            return True
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_koordinator or user.profile.is_admin


# ---------------------------------------------------------------------------
# Registration Views (public — no login required)
# ---------------------------------------------------------------------------


class RegistrationView(FormView):
    """
    Token-based registration. Koordinator sends this link to the betreuer.
    No login required. Creates User + UserProfile + BetreuerProfile + Contract(draft).
    """

    template_name = "contracts/registration_form.html"
    form_class = BetreuerRegistrationForm
    success_url = reverse_lazy("contracts:registration_success")

    def dispatch(self, request, *args, **kwargs):
        self.reg_link = get_object_or_404(
            RegistrationLink, token=kwargs["token"]
        )
        if not self.reg_link.is_valid:
            return render(
                request, "contracts/registration_link_invalid.html", status=410
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["school_from_token"] = self.reg_link.school
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["school"] = self.reg_link.school
        return ctx

    def form_valid(self, form):
        user, betreuer_profile, contract, is_duplicate = _create_betreuer_from_form(form)
        self.reg_link.mark_used(user)
        if is_duplicate:
            messages.info(
                self.request,
                "Willkommen zurueck! Ein neuer Vertrag wurde fuer Sie angelegt.",
            )
        messages.success(self.request, "Registrierung erfolgreich!")
        return super().form_valid(form)


class PublicRegistrationView(FormView):
    """
    Public self-service registration (no token required).
    Betreuer selects school themselves. School field is not locked.

    Security: rate-limited to 5 registrations per IP per hour via session.
    """

    template_name = "contracts/registration_form.html"
    form_class = BetreuerRegistrationForm
    success_url = reverse_lazy("contracts:registration_success")

    def dispatch(self, request, *args, **kwargs):
        # Simple IP-based rate limiting via Django cache
        from django.core.cache import cache

        ip = request.META.get("REMOTE_ADDR", "unknown")
        cache_key = f"reg_rate_{ip}"
        attempts = cache.get(cache_key, 0)

        if request.method == "POST" and attempts >= 5:
            messages.error(
                request,
                "Zu viele Registrierungsversuche. Bitte versuchen Sie es spaeter erneut.",
            )
            return redirect("contracts:public_registration")

        if request.method == "POST":
            cache.set(cache_key, attempts + 1, timeout=3600)  # 1 hour

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user, betreuer_profile, contract, is_duplicate = _create_betreuer_from_form(form)
        if is_duplicate:
            messages.info(
                self.request,
                "Willkommen zurueck! Ein neuer Vertrag wurde fuer Sie angelegt.",
            )
        messages.success(self.request, "Registrierung erfolgreich!")
        return super().form_valid(form)


class RegistrationSuccessView(TemplateView):
    """Confirmation page after successful registration."""

    template_name = "contracts/registration_success.html"


# ---------------------------------------------------------------------------
# Registration Link Management (Koordinator / Admin)
# ---------------------------------------------------------------------------


class CreateRegistrationLinkView(KoordinatorOrAdminMixin, FormView):
    """Koordinator/Admin creates a registration link for a specific school."""

    template_name = "contracts/create_registration_link.html"
    form_class = RegistrationLinkForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        profile = self.request.user.profile
        if profile.is_koordinator:
            kwargs["koordinator_schools"] = profile.schools.filter(is_active=True)
        return kwargs

    def form_valid(self, form):
        cd = form.cleaned_data
        link = RegistrationLink.objects.create(
            school=cd["school"],
            created_by=self.request.user,
            is_single_use=cd["is_single_use"],
            expires_at=timezone.now() + timedelta(days=cd["expires_in_days"]),
            notes=cd.get("notes", ""),
        )
        reg_url = self.request.build_absolute_uri(f"/registrierung/{link.token}/")
        messages.success(
            self.request,
            f"Registrierungslink erstellt: {reg_url}",
        )
        return redirect("contracts:registration_link_list")


class RegistrationLinkListView(KoordinatorOrAdminMixin, ListView):
    """List registration links for the Koordinator's schools."""

    template_name = "contracts/registration_link_list.html"
    context_object_name = "links"

    def get_queryset(self):
        user = self.request.user
        # Superusers and admins see all links
        if user.is_superuser or (hasattr(user, "profile") and user.profile.is_admin):
            return RegistrationLink.objects.select_related(
                "school", "created_by"
            ).all()
        profile = user.profile
        return RegistrationLink.objects.filter(
            school__in=profile.schools.all()
        ).select_related("school", "created_by")


# ---------------------------------------------------------------------------
# Betreuer Management (Koordinator / Admin)
# ---------------------------------------------------------------------------


class BetreuerListView(KoordinatorOrAdminMixin, ListView):
    """List betreuer profiles, scoped to Koordinator's schools or all for Admin."""

    template_name = "contracts/betreuer_list.html"
    context_object_name = "betreuer_list"

    def get_queryset(self):
        user = self.request.user
        qs = BetreuerProfile.objects.select_related("user").prefetch_related(
            "contracts__school"
        )
        # Superusers and admins see all betreuer profiles
        if user.is_superuser or (hasattr(user, "profile") and user.profile.is_admin):
            return qs
        profile = user.profile
        if profile.is_koordinator:
            school_ids = profile.schools.values_list("id", flat=True)
            qs = qs.filter(contracts__school_id__in=school_ids).distinct()
        return qs


class BetreuerDetailView(KoordinatorOrAdminMixin, DetailView):
    """Detail view for a single betreuer, including onboarding checklist."""

    model = BetreuerProfile
    template_name = "contracts/betreuer_detail.html"
    context_object_name = "betreuer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["contracts"] = self.object.contracts.select_related(
            "school", "activity_type", "hourly_rate"
        ).prefetch_related("foerderprogramme")
        documents = Document.objects.filter(
            betreuer=self.object
        ).select_related("requirement", "contract")
        ctx["documents"] = documents
        ctx["has_pending_documents"] = documents.filter(status="pending").exists()
        ctx["has_generated_documents"] = documents.filter(status="generated").exists()
        return ctx


class BetreuerReviewView(KoordinatorOrAdminMixin, View):
    """
    Koordinator reviews betreuer data and confirms the hourly rate.
    On POST: transitions BetreuerProfile to 'documents_pending'.
    """

    def get(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        contracts = betreuer.contracts.select_related(
            "school", "activity_type", "hourly_rate", "school_year",
        ).prefetch_related("foerderprogramme")
        return render(
            request,
            "contracts/betreuer_review.html",
            {"betreuer": betreuer, "contracts": contracts},
        )

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        if betreuer.can_transition_to("approved"):
            betreuer.transition_to("approved")
            messages.success(
                request,
                "Betreuer wurde genehmigt. Dokumente koennen nach der Freigabe generiert werden.",
            )
        elif betreuer.can_transition_to("documents_pending"):
            betreuer.transition_to("documents_pending")
            messages.success(
                request,
                "Betreuer-Daten bestaetigt. Dokumente koennen nun generiert werden.",
            )
        else:
            messages.error(
                request,
                f"Statusuebergang nicht moeglich. "
                f"Aktueller Status: {betreuer.get_onboarding_status_display()}",
            )
        return redirect("contracts:betreuer_detail", pk=pk)


class BetreuerActivateView(KoordinatorOrAdminMixin, View):
    """Koordinator activates a betreuer after all documents are verified."""

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        if betreuer.can_transition_to("active"):
            betreuer.transition_to("active")
            messages.success(
                request,
                f"{betreuer.user.get_full_name()} ist jetzt aktiv.",
            )
        else:
            messages.error(
                request,
                f"Aktivierung nicht moeglich. "
                f"Aktueller Status: {betreuer.get_onboarding_status_display()}",
            )
        return redirect("contracts:betreuer_detail", pk=pk)


class BetreuerUpdateAccountingView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin-only: set or update Projektnummer and Kreditorennummer
    for a BetreuerProfile. Triggers no status transition.
    """

    raise_exception = True

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        if not hasattr(user, "profile"):
            return False
        return user.profile.is_admin

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        projektnummer = request.POST.get("projektnummer", "").strip()
        kreditorennummer = request.POST.get("kreditorennummer", "").strip()

        errors = []

        # Validate projektnummer (8 digits or blank)
        if projektnummer and (not projektnummer.isdigit() or len(projektnummer) != 8):
            errors.append("Projektnummer muss genau 8 Ziffern enthalten.")

        # Validate kreditorennummer (5 digits or blank)
        if kreditorennummer and (not kreditorennummer.isdigit() or len(kreditorennummer) != 5):
            errors.append("Kreditorennummer muss genau 5 Ziffern enthalten.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return redirect("contracts:betreuer_detail", pk=pk)

        betreuer.projektnummer = projektnummer
        betreuer.kreditorennummer = kreditorennummer
        betreuer.save(update_fields=["projektnummer", "kreditorennummer", "updated_at"])

        if projektnummer and kreditorennummer:
            messages.success(
                request,
                f"Buchhaltungsdaten gespeichert. "
                f"QR-Code wird ab dem naechsten PDF-Ausdruck sichtbar.",
            )
        else:
            messages.info(request, "Buchhaltungsdaten gespeichert (QR-Code deaktiviert).")

        return redirect("contracts:betreuer_detail", pk=pk)


# ---------------------------------------------------------------------------
# HTMX Rate Lookup
# ---------------------------------------------------------------------------


class RateLookupView(View):
    """
    HTMX endpoint: returns the hourly rate for a given
    activity_type + betreuer_type + hour_duration combination.
    """

    def get(self, request):
        activity_type_id = request.GET.get("activity_type")
        betreuer_type = request.GET.get("betreuer_type")
        hour_duration = request.GET.get("hour_duration", "60")

        if not activity_type_id or not betreuer_type:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        school_year = SchoolYear.objects.filter(is_current=True).first()
        if not school_year:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        try:
            activity_type = ActivityType.objects.get(pk=activity_type_id)
        except ActivityType.DoesNotExist:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        rate = HourlyRate.get_current_rate(activity_type, betreuer_type, school_year)
        if not rate:
            return render(
                request,
                "contracts/partials/_rate_display.html",
                {"rate": None, "message": "Kein Satz gefunden."},
            )

        effective = rate.rate_45min if hour_duration == "45" else rate.rate_60min
        return render(
            request,
            "contracts/partials/_rate_display.html",
            {
                "rate": effective,
                "rate_60": rate.rate_60min,
                "rate_45": rate.rate_45min,
            },
        )


# ---------------------------------------------------------------------------
# HTMX Cascading Lookups (Foerderprogramm -> ActivityType)
# ---------------------------------------------------------------------------


class FoerderprogrammLookupView(View):
    """
    HTMX endpoint: returns Foerderprogramm options for a given school.
    Filters programmes by school category (grundschule vs. weiterfuehrend).
    """

    def get(self, request):
        school_id = request.GET.get("school")
        if not school_id:
            return render(
                request,
                "contracts/partials/_foerderprogramm_select.html",
                {"programmes": []},
            )
        try:
            school = School.objects.get(pk=school_id)
        except (School.DoesNotExist, ValueError):
            return render(
                request,
                "contracts/partials/_foerderprogramm_select.html",
                {"programmes": []},
            )

        school_year = SchoolYear.objects.filter(is_current=True).first()
        programmes = Foerderprogramm.get_for_school(school, school_year)
        return render(
            request,
            "contracts/partials/_foerderprogramm_select.html",
            {"programmes": programmes},
        )


class ActivityTypeLookupView(View):
    """
    HTMX endpoint: returns ActivityType options for a given Foerderprogramm.
    """

    def get(self, request):
        programm_id = request.GET.get("foerderprogramm")
        if not programm_id:
            return render(
                request,
                "contracts/partials/_activity_type_select.html",
                {"activity_types": []},
            )
        try:
            programm = Foerderprogramm.objects.get(pk=programm_id)
        except (Foerderprogramm.DoesNotExist, ValueError):
            return render(
                request,
                "contracts/partials/_activity_type_select.html",
                {"activity_types": []},
            )

        activity_types = programm.activity_types.filter(is_active=True)
        return render(
            request,
            "contracts/partials/_activity_type_select.html",
            {"activity_types": activity_types},
        )


# ---------------------------------------------------------------------------
# Helper functions (shared by RegistrationView and PublicRegistrationView)
# ---------------------------------------------------------------------------


def _create_betreuer_from_form(form):
    """
    Create User + UserProfile + BetreuerProfile + Contract from a
    validated BetreuerRegistrationForm.

    V2 Changes:
    - Betreuer sets own password during registration.
    - Hash-based duplicate detection: if a Betreuer is already known,
      a new contract is created for the existing profile.
    - Status transitions to pending_approval after creation.
    - start_date is left null (set later by Koordinator).

    Returns (user, betreuer_profile, contract, is_duplicate).
    """
    from apps.contracts.services import (
        check_duplicate_registration,
        check_email_mismatch,
        generate_unique_hash,
    )
    from apps.notifications.services import (
        notify_contract_created,
        notify_duplicate_detected,
        notify_email_mismatch,
        notify_pending_approval,
    )

    cd = form.cleaned_data

    # --- Check for duplicate via hash ---
    hash_value = generate_unique_hash(
        cd["first_name"], cd["last_name"], cd["geburtsdatum"]
    )
    is_duplicate, existing_profile = check_duplicate_registration(hash_value)

    if is_duplicate and existing_profile:
        # Returning Betreuer: create a new contract for the existing profile
        user = existing_profile.user
        betreuer_profile = existing_profile
    else:
        # New Betreuer: create User + profiles
        username = cd["email"].split("@")[0].lower()
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=cd["email"],
            first_name=cd["first_name"],
            last_name=cd["last_name"],
            password=cd.get("password", None),
        )
        if not cd.get("password"):
            user.set_unusable_password()
        user.save()

        UserProfile.objects.create(user=user, role="betreuer")

        is_external = cd["betreuer_type"] == "extern"

        betreuer_profile = BetreuerProfile.objects.create(
            user=user,
            anrede=cd["anrede"],
            geburtsdatum=cd["geburtsdatum"],
            geschlecht=cd["geschlecht"],
            staatsangehoerigkeit=cd["staatsangehoerigkeit"],
            street=cd["street"],
            house_number=cd["house_number"],
            plz=cd["plz"],
            city=cd["city"],
            kontoinhaber=cd["kontoinhaber"],
            iban=cd["iban"],
            bic=cd.get("bic", ""),
            betreuer_type=cd["betreuer_type"],
            is_external=is_external,
            freibetrag_used_elsewhere=cd.get("freibetrag_used_elsewhere", False),
            freibetrag_amount_elsewhere=cd.get("freibetrag_amount_elsewhere") or 0,
            freibetrag_verein_name=cd.get("freibetrag_verein_name", ""),
            unique_hash=hash_value,
            onboarding_status="registered",
        )

    # --- Look up hourly rate ---
    school_year = SchoolYear.objects.filter(is_current=True).first()
    hourly_rate = HourlyRate.get_current_rate(
        activity_type=cd["activity_type"],
        betreuer_type=cd["betreuer_type"],
        school_year=school_year,
    )

    # --- Create Contract (draft) — start_date is null until Koordinator approval ---
    contract_number = Contract.generate_contract_number(
        school_code=cd["school"].code,
        school_year=school_year,
    )
    contract = Contract.objects.create(
        contract_number=contract_number,
        betreuer=betreuer_profile,
        school=cd["school"],
        school_year=school_year,
        activity_type=cd["activity_type"],
        hourly_rate=hourly_rate,
        hour_duration=int(cd["hour_duration"]),
        ag_name=cd.get("ag_name", ""),
        start_date=None,
        end_date=school_year.end_date,
        status="draft",
    )
    if cd.get("foerderprogramm"):
        contract.foerderprogramme.add(cd["foerderprogramm"])

    # --- Create pending documents ---
    _create_pending_documents(contract, betreuer_profile)

    # --- Transition to pending_approval ---
    if betreuer_profile.onboarding_status == "registered":
        betreuer_profile.transition_to("pending_approval")

    # --- Email mismatch check ---
    email_mismatch = False
    try:
        has_mismatch, stored_email = check_email_mismatch(hash_value, cd["email"])
        if has_mismatch:
            email_mismatch = True
            logger.info(
                "Email mismatch for %s: form=%s, stored=%s",
                user.get_full_name(), cd["email"], stored_email,
            )
    except Exception:
        logger.warning("Email mismatch check failed for %s", user.email)

    # --- N8N notifications ---
    try:
        notify_pending_approval(betreuer_profile, contract)
        notify_contract_created(contract)
        if is_duplicate and existing_profile:
            notify_duplicate_detected(betreuer_profile, existing_profile)
        if email_mismatch:
            notify_email_mismatch(user.get_full_name(), cd["email"], stored_email)
    except Exception:
        logger.warning(
            "N8N notification failed for registration of %s",
            user.email,
        )

    return user, betreuer_profile, contract, is_duplicate


def _create_pending_documents(contract, betreuer_profile):
    """
    Create Document entries in 'pending' status for all applicable
    DocumentRequirements based on the betreuer's classification.
    """
    requirements = DocumentRequirement.objects.all()
    for req in requirements:
        if req.is_required_for(betreuer_profile):
            Document.objects.get_or_create(
                contract=contract,
                requirement=req,
                defaults={
                    "betreuer": betreuer_profile,
                    "status": "pending",
                },
            )


# ---------------------------------------------------------------------------
# Koordinator Approval (V2)
# ---------------------------------------------------------------------------


class ApprovalView(KoordinatorOrAdminMixin, View):
    """
    Koordinator approves a pending betreuer registration.

    Sets: Foerderprogramm, Vertragsbeginn, Betreuer-Typ, AG-Name.
    Transitions BetreuerProfile from pending_approval -> approved.
    """

    def get(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        contracts = betreuer.contracts.select_related(
            "school", "activity_type", "hourly_rate", "school_year",
        ).prefetch_related("foerderprogramme")

        from apps.contracts.forms import ApprovalForm
        form = ApprovalForm(betreuer_profile=betreuer)

        return render(
            request,
            "contracts/approval_form.html",
            {"betreuer": betreuer, "contracts": contracts, "form": form},
        )

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)

        from apps.contracts.forms import ApprovalForm
        form = ApprovalForm(request.POST, betreuer_profile=betreuer)

        if not form.is_valid():
            contracts = betreuer.contracts.select_related(
                "school", "activity_type", "hourly_rate", "school_year",
            ).prefetch_related("foerderprogramme")
            return render(
                request,
                "contracts/approval_form.html",
                {"betreuer": betreuer, "contracts": contracts, "form": form},
            )

        cd = form.cleaned_data
        contract = betreuer.contracts.order_by("-created_at").first()

        if contract:
            # Update contract fields set by Koordinator
            contract.start_date = cd["start_date"]
            if cd.get("ag_name"):
                contract.ag_name = cd["ag_name"]
            contract.save(update_fields=["start_date", "ag_name", "updated_at"])

            if cd.get("foerderprogramm"):
                contract.foerderprogramme.clear()
                contract.foerderprogramme.add(cd["foerderprogramm"])

        # Update betreuer type if changed
        if cd.get("betreuer_type"):
            betreuer.betreuer_type = cd["betreuer_type"]
            betreuer.save(update_fields=["betreuer_type", "updated_at"])

        # Transition status
        if betreuer.can_transition_to("approved"):
            betreuer.transition_to("approved")

            from apps.notifications.services import notify_betreuer_approved
            try:
                notify_betreuer_approved(betreuer, contract)
            except Exception:
                logger.warning(
                    "N8N notification failed for approval of betreuer %s",
                    betreuer.pk,
                )

            messages.success(
                request,
                f"{betreuer.user.get_full_name()} wurde genehmigt.",
            )
        else:
            messages.error(
                request,
                f"Genehmigung nicht moeglich. "
                f"Aktueller Status: {betreuer.get_onboarding_status_display()}",
            )

        return redirect("contracts:betreuer_detail", pk=pk)


# ---------------------------------------------------------------------------
# HTMX Hash Check (V2)
# ---------------------------------------------------------------------------


class HashCheckView(View):
    """
    HTMX endpoint: checks if a betreuer with the given name + birthdate
    already exists. Returns a partial with duplicate info or empty.
    """

    def get(self, request):
        first_name = request.GET.get("first_name", "")
        last_name = request.GET.get("last_name", "")
        geburtsdatum_str = request.GET.get("geburtsdatum", "")

        if not (first_name and last_name and geburtsdatum_str):
            return render(request, "contracts/partials/_hash_check.html", {"duplicate": None})

        from datetime import date as date_cls
        try:
            geburtsdatum = date_cls.fromisoformat(geburtsdatum_str)
        except (ValueError, TypeError):
            return render(request, "contracts/partials/_hash_check.html", {"duplicate": None})

        from apps.contracts.services import (
            check_duplicate_registration,
            generate_unique_hash,
        )
        hash_value = generate_unique_hash(first_name, last_name, geburtsdatum)
        is_duplicate, existing_profile = check_duplicate_registration(hash_value)

        return render(
            request,
            "contracts/partials/_hash_check.html",
            {"duplicate": existing_profile if is_duplicate else None},
        )
