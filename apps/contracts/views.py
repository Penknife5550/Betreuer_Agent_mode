"""
Views for the contracts app.

Covers: Betreuer registration (token + public), registration link management,
betreuer list/detail/review/activate, Koordinator approval, HTMX endpoints.

Sicherheits-Invarianten:
- Koordinator-Aktionen haben immer einen Scope-Check ueber
  ``require_scope_access`` (Betreuer muss Vertrag an einer Schule des
  Koordinators haben).
- Registrierung laeuft atomar im Service-Layer; n8n-Notifications werden
  erst nach Commit asynchron via django-q2 ausgeloest.
- Rate-Limit nutzt die echte Client-IP aus dem AuditLogMiddleware
  (X-Forwarded-For-aware), nicht REMOTE_ADDR (= Caddy-IP).
"""

import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.contracts.forms import (
    ApprovalForm,
    BetreuerRegistrationForm,
    RegistrationLinkForm,
)
from apps.contracts.models import BetreuerProfile, RegistrationLink
from apps.contracts.services import (
    _create_pending_documents,  # re-export fuer bestehende Tests
    approve_betreuer,
    check_duplicate_registration,
    generate_unique_hash,
    register_betreuer_from_form,
    send_registration_invite,
    RegistrationUnavailable,
)
from apps.core.middleware import get_current_ip
from apps.core.permissions import (
    AdminOnlyMixin,
    KoordinatorOrAdminMixin,
    KoordinatorScopedMixin,
    has_admin_role,
    require_scope_access,
)
from apps.core.utils import safe_get_by_id
from apps.documents.models import Document
from apps.documents.services import mask_iban
from apps.rates.models import ActivityType, HourlyRate
from apps.schools.models import Foerderprogramm, School, SchoolYear

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

REG_RATE_LIMIT_PER_HOUR = 5
REG_RATE_LIMIT_WINDOW_S = 3600
HASH_CHECK_LIMIT_PER_HOUR = 20  # weniger als Registrierungen, da billiger

_REGISTRATION_UNAVAILABLE_MSG = (
    "Die Registrierung ist derzeit nicht moeglich (Grundkonfiguration "
    "unvollstaendig). Bitte wenden Sie sich an Ihre Koordination."
)


def _client_ip_for_rate_limit(request):
    """
    Liefert die echte Client-IP fuer Rate-Limiting.
    Bevorzugt X-Forwarded-For (ueber AuditLogMiddleware in thread-local),
    faellt auf REMOTE_ADDR zurueck. Der Wert "unknown" wird bewusst
    beibehalten, falls beide Quellen fehlen.
    """
    return get_current_ip() or request.META.get("REMOTE_ADDR") or "unknown"


# ---------------------------------------------------------------------------
# Registrierung (oeffentlich, ohne Login)
# ---------------------------------------------------------------------------


class RegistrationView(FormView):
    """
    Token-basierte Registrierung. Koordinator verschickt den Link an den
    Betreuer. Kein Login noetig.
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
        try:
            user, betreuer_profile, contract, is_duplicate = register_betreuer_from_form(form)
        except RegistrationUnavailable:
            messages.error(self.request, _REGISTRATION_UNAVAILABLE_MSG)
            return self.form_invalid(form)
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
    Oeffentliche Self-Service-Registrierung (ohne Token).

    Rate-Limit: REG_RATE_LIMIT_PER_HOUR POSTs pro echter Client-IP und
    Stunde. Der Cache-Key nutzt ``get_current_ip()`` aus der
    AuditLogMiddleware, damit Caddy als Reverse-Proxy nicht zur
    geteilten Source-IP wird (sonst globaler DoS moeglich).
    """

    template_name = "contracts/registration_form.html"
    form_class = BetreuerRegistrationForm
    success_url = reverse_lazy("contracts:registration_success")

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            ip = _client_ip_for_rate_limit(request)
            cache_key = f"reg_rate:{ip}"
            attempts = cache.get(cache_key, 0)
            if attempts >= REG_RATE_LIMIT_PER_HOUR:
                messages.error(
                    request,
                    "Zu viele Registrierungsversuche. "
                    "Bitte versuchen Sie es spaeter erneut.",
                )
                return redirect("contracts:public_registration")
            cache.set(cache_key, attempts + 1, timeout=REG_RATE_LIMIT_WINDOW_S)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            user, betreuer_profile, contract, is_duplicate = register_betreuer_from_form(form)
        except RegistrationUnavailable:
            messages.error(self.request, _REGISTRATION_UNAVAILABLE_MSG)
            return self.form_invalid(form)
        if is_duplicate:
            messages.info(
                self.request,
                "Willkommen zurueck! Ein neuer Vertrag wurde fuer Sie angelegt.",
            )
        messages.success(self.request, "Registrierung erfolgreich!")
        return super().form_valid(form)


class RegistrationSuccessView(TemplateView):
    """Bestaetigungsseite nach erfolgreicher Registrierung."""

    template_name = "contracts/registration_success.html"


# ---------------------------------------------------------------------------
# Registration-Link-Verwaltung (Koordinator / Admin)
# ---------------------------------------------------------------------------


class CreateRegistrationLinkView(KoordinatorOrAdminMixin, FormView):
    template_name = "contracts/create_registration_link.html"
    form_class = RegistrationLinkForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Superuser haben ggf. kein UserProfile -- dann sehen sie alle Schulen.
        profile = getattr(self.request.user, "profile", None)
        if profile and profile.is_koordinator and not profile.is_admin:
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
            sent_to=cd["email"],
            recipient_name=cd["recipient_name"],
        )
        sent = send_registration_invite(link)
        if sent:
            messages.success(
                self.request,
                f"Registrierungslink wurde erstellt und an {link.sent_to} "
                f"verschickt.",
            )
        else:
            messages.warning(
                self.request,
                f"Link erstellt, aber die E-Mail an {link.sent_to} konnte nicht "
                f"versendet werden. Bitte SMTP-Konfiguration pruefen und in der "
                f"Uebersicht erneut senden.",
            )
        return redirect("contracts:registration_link_list")


class RegistrationLinkListView(KoordinatorOrAdminMixin, ListView):
    template_name = "contracts/registration_link_list.html"
    context_object_name = "links"

    def get_queryset(self):
        user = self.request.user
        if has_admin_role(user):
            return RegistrationLink.objects.select_related(
                "school", "created_by"
            ).all()
        profile = user.profile
        return RegistrationLink.objects.filter(
            school__in=profile.schools.all()
        ).select_related("school", "created_by")


class ResendRegistrationLinkView(KoordinatorOrAdminMixin, View):
    """Verschickt die Einladung eines bestehenden Links erneut (Direktversand)."""

    def post(self, request, pk):
        user = request.user
        if has_admin_role(user):
            link = get_object_or_404(RegistrationLink, pk=pk)
        else:
            # Koordinator: nur Links der eigenen Schulen (Scope via Query -> 404).
            profile = user.profile
            link = get_object_or_404(
                RegistrationLink, pk=pk, school__in=profile.schools.all()
            )

        if not link.sent_to:
            messages.error(
                request, "Fuer diesen Link ist keine E-Mail-Adresse hinterlegt."
            )
        elif send_registration_invite(link):
            messages.success(
                request, f"Einladung wurde erneut an {link.sent_to} verschickt."
            )
        else:
            messages.warning(
                request,
                f"Erneuter Versand an {link.sent_to} fehlgeschlagen. "
                f"Bitte SMTP-Konfiguration pruefen.",
            )
        return redirect("contracts:registration_link_list")


# ---------------------------------------------------------------------------
# Betreuer-Verwaltung (Koordinator / Admin)
# ---------------------------------------------------------------------------


class BetreuerListView(KoordinatorOrAdminMixin, ListView):
    """Liste aller Betreuer, scoped auf die Schulen des Koordinators."""

    template_name = "contracts/betreuer_list.html"
    context_object_name = "betreuer_list"
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        qs = (
            BetreuerProfile.objects
            .select_related("user")
            .prefetch_related("contracts__school")
        )
        if has_admin_role(user):
            return qs
        profile = user.profile
        if profile.is_koordinator:
            school_ids = profile.schools.values_list("id", flat=True)
            qs = qs.filter(contracts__school_id__in=school_ids).distinct()
        return qs


class BetreuerDetailView(KoordinatorScopedMixin, DetailView):
    """
    Detail-Ansicht fuer einen Betreuer. Nicht-Admin-Koordinatoren
    sehen nur Betreuer mit Vertraegen an ihren Schulen (IDOR-Schutz).

    Scope-Check laeuft doppelgleisig:
    1. ``get_queryset`` filtert auf Betreuer mit Contracts an
       Koordinator-Schulen (-> 404 bei Nicht-Schnittmenge).
    2. ``KoordinatorScopedMixin.get_object`` ruft zusaetzlich
       ``require_scope_access`` auf (Defense-in-Depth).
    """

    model = BetreuerProfile
    template_name = "contracts/betreuer_detail.html"
    context_object_name = "betreuer"

    def get_queryset(self):
        user = self.request.user
        qs = BetreuerProfile.objects.select_related("user")
        if has_admin_role(user):
            return qs
        profile = getattr(user, "profile", None)
        if profile and profile.is_koordinator:
            school_ids = profile.schools.values_list("id", flat=True)
            return qs.filter(contracts__school_id__in=school_ids).distinct()
        return qs.none()

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
        # IBAN nur maskiert anzeigen -- konsistent mit Profil-Seite und PDFs.
        ctx["iban_masked"] = mask_iban(self.object.iban)
        return ctx


class BetreuerReviewView(KoordinatorOrAdminMixin, View):
    """Koordinator prueft Betreuer-Daten und bestaetigt den Stundensatz."""

    def _get_betreuer(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        require_scope_access(request.user, betreuer)
        return betreuer

    def get(self, request, pk):
        betreuer = self._get_betreuer(request, pk)
        contracts = betreuer.contracts.select_related(
            "school", "activity_type", "hourly_rate", "school_year",
        ).prefetch_related("foerderprogramme")
        return render(
            request,
            "contracts/betreuer_review.html",
            {"betreuer": betreuer, "contracts": contracts},
        )

    def post(self, request, pk):
        betreuer = self._get_betreuer(request, pk)
        if betreuer.can_transition_to("approved"):
            betreuer.transition_to("approved")
            messages.success(
                request,
                "Betreuer wurde genehmigt. "
                "Dokumente koennen nach der Freigabe generiert werden.",
            )
        elif betreuer.can_transition_to("documents_pending"):
            betreuer.transition_to("documents_pending")
            messages.success(
                request,
                "Betreuer-Daten bestaetigt. "
                "Dokumente koennen nun generiert werden.",
            )
        else:
            messages.error(
                request,
                f"Statusuebergang nicht moeglich. "
                f"Aktueller Status: {betreuer.get_onboarding_status_display()}",
            )
        return redirect("contracts:betreuer_detail", pk=pk)


class BetreuerActivateView(KoordinatorOrAdminMixin, View):
    """Koordinator aktiviert einen Betreuer nach Dokumenten-Verifikation."""

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        require_scope_access(request.user, betreuer)
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


class BetreuerUpdateAccountingView(AdminOnlyMixin, View):
    """
    Admin-only: setzt oder aktualisiert Projektnummer und Kreditorennummer
    eines BetreuerProfiles. Kein Status-Uebergang.
    """

    def post(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        projektnummer = request.POST.get("projektnummer", "").strip()
        kreditorennummer = request.POST.get("kreditorennummer", "").strip()

        errors = []
        if projektnummer and (not projektnummer.isdigit() or len(projektnummer) != 8):
            errors.append("Projektnummer muss genau 8 Ziffern enthalten.")
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
                "Buchhaltungsdaten gespeichert. "
                "QR-Code wird ab dem naechsten PDF-Ausdruck sichtbar.",
            )
        else:
            messages.info(
                request,
                "Buchhaltungsdaten gespeichert (QR-Code deaktiviert).",
            )

        return redirect("contracts:betreuer_detail", pk=pk)


# ---------------------------------------------------------------------------
# Koordinator-Approval (V2)
# ---------------------------------------------------------------------------


class ApprovalView(KoordinatorOrAdminMixin, View):
    """Koordinator genehmigt eine pending_approval-Registrierung."""

    def _get_betreuer(self, request, pk):
        betreuer = get_object_or_404(BetreuerProfile, pk=pk)
        require_scope_access(request.user, betreuer)
        return betreuer

    def get(self, request, pk):
        betreuer = self._get_betreuer(request, pk)
        contracts = betreuer.contracts.select_related(
            "school", "activity_type", "hourly_rate", "school_year",
        ).prefetch_related("foerderprogramme")

        form = ApprovalForm(betreuer_profile=betreuer)

        return render(
            request,
            "contracts/approval_form.html",
            {"betreuer": betreuer, "contracts": contracts, "form": form},
        )

    def post(self, request, pk):
        betreuer = self._get_betreuer(request, pk)

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

        success = approve_betreuer(betreuer, form.cleaned_data)
        if success:
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
# HTMX: Rate / Foerderprogramm / ActivityType / Hash-Check (oeffentlich)
# ---------------------------------------------------------------------------


class RateLookupView(View):
    """HTMX: Stundensatz fuer activity_type + betreuer_type + hour_duration."""

    def get(self, request):
        activity_type_id = request.GET.get("activity_type")
        betreuer_type = request.GET.get("betreuer_type")
        hour_duration = request.GET.get("hour_duration", "60")

        if not activity_type_id or not betreuer_type:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        school_year = SchoolYear.objects.filter(is_current=True).first()
        if not school_year:
            return render(request, "contracts/partials/_rate_display.html", {"rate": None})

        activity_type = safe_get_by_id(ActivityType, activity_type_id)
        if activity_type is None:
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


class FoerderprogrammLookupView(View):
    """HTMX: Foerderprogramme fuer eine Schule."""

    def get(self, request):
        school_id = request.GET.get("school")
        school = safe_get_by_id(School, school_id)
        if school is None:
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
    """HTMX: ActivityTypes fuer ein Foerderprogramm."""

    def get(self, request):
        programm_id = request.GET.get("foerderprogramm")
        programm = safe_get_by_id(Foerderprogramm, programm_id)
        if programm is None:
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


class HashCheckView(View):
    """
    HTMX: prueft ob ein Betreuer mit Name + Geburtsdatum bereits existiert.

    Rate-Limit: HASH_CHECK_LIMIT_PER_HOUR pro echter Client-IP, um
    Personenenumeration durch externe Aufrufer einzudaemmen. Antwort ist
    zusaetzlich bewusst generisch (keine E-Mail, keine Schule).
    """

    def get(self, request):
        ip = _client_ip_for_rate_limit(request)
        cache_key = f"hash_check:{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= HASH_CHECK_LIMIT_PER_HOUR:
            # Generisches Leerpartial -- keine Preisgabe dass Throttling aktiv
            return render(
                request,
                "contracts/partials/_hash_check.html",
                {"duplicate": None},
            )
        cache.set(cache_key, attempts + 1, timeout=3600)

        first_name = request.GET.get("first_name", "").strip()
        last_name = request.GET.get("last_name", "").strip()
        geburtsdatum_str = request.GET.get("geburtsdatum", "").strip()

        if not (first_name and last_name and geburtsdatum_str):
            return render(request, "contracts/partials/_hash_check.html", {"duplicate": None})

        from datetime import date as date_cls
        try:
            geburtsdatum = date_cls.fromisoformat(geburtsdatum_str)
        except (ValueError, TypeError):
            return render(request, "contracts/partials/_hash_check.html", {"duplicate": None})

        hash_value = generate_unique_hash(first_name, last_name, geburtsdatum)
        is_duplicate, existing_profile = check_duplicate_registration(hash_value)
        return render(
            request,
            "contracts/partials/_hash_check.html",
            {"duplicate": existing_profile if is_duplicate else None},
        )
