"""
Views for the timetracking app.

Covers: Time entry CRUD (Betreuer), timesheet submission (Betreuer),
timesheet review / approval / rejection (Koordinator/Admin),
PDF download for approved timesheets.
"""

import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.contracts.models import Contract
from apps.core.permissions import BetreuerOnlyMixin as BetreuerRequiredMixin
from apps.core.permissions import KoordinatorOrAdminMixin
from apps.timetracking.forms import TimeEntryForm
from apps.timetracking.models import MonthlyTimesheet, TimeEntry

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Betreuer: Time Entry Views
# ------------------------------------------------------------------


class TimeEntryListView(BetreuerRequiredMixin, TemplateView):
    """
    Monthly view of time entries for the logged-in Betreuer.

    Delegiert die Context-Berechnung an
    ``apps.timetracking.services.get_monthly_time_entry_context`` --
    die View selbst behandelt nur das HTTP/GET-Parameter-Parsing.
    """

    template_name = "timetracking/time_entry_list.html"

    def get_context_data(self, **kwargs):
        from apps.timetracking.services import get_monthly_time_entry_context

        context = super().get_context_data(**kwargs)

        today = date.today()
        try:
            month = int(self.request.GET.get("month", today.month))
            year = int(self.request.GET.get("year", today.year))
        except (ValueError, TypeError):
            month, year = today.month, today.year
        month = max(1, min(12, month))

        school_filter_id = self.request.GET.get("school_filter")

        context.update(
            get_monthly_time_entry_context(
                self.request.user,
                month=month,
                year=year,
                school_filter_id=school_filter_id,
            )
        )
        return context


class TimeEntryCreateView(BetreuerRequiredMixin, View):
    """Create a new time entry (HTMX or standard POST)."""

    def get(self, request):
        """Return the entry form (HTMX partial or full page)."""
        contract_id = request.GET.get("contract")
        initial = {}
        if contract_id:
            initial["contract"] = contract_id
        form = TimeEntryForm(initial=initial)

        if request.htmx:
            html = render_to_string(
                "timetracking/partials/_time_entry_form.html",
                {"form": form},
                request=request,
            )
            return HttpResponse(html)
        return render(request, "timetracking/partials/_time_entry_form.html", {"form": form})

    def post(self, request):
        """Process the form submission."""
        form = TimeEntryForm(request.POST, contract=None)
        if form.is_valid():
            entry = form.save(commit=False)
            # Verify ownership
            betreuer_profile = getattr(request.user, "betreuer_profile", None)
            if not betreuer_profile or entry.contract.betreuer_id != betreuer_profile.pk:
                messages.error(request, "Keine Berechtigung fuer diesen Vertrag.")
                return redirect("timetracking:time_entry_list")

            # Block new entries if a submitted/approved timesheet exists for this month
            locked_timesheet = MonthlyTimesheet.objects.filter(
                contract=entry.contract,
                month=entry.date.month,
                year=entry.date.year,
                status__in=("submitted", "approved"),
            ).first()
            if locked_timesheet:
                messages.error(
                    request,
                    f"Fuer {entry.date.month:02d}/{entry.date.year} wurde bereits ein "
                    f"Stundennachweis eingereicht. Neue Eintraege sind gesperrt.",
                )
                return redirect(
                    f"/stunden/?year={entry.date.year}&month={entry.date.month}"
                )

            entry.full_clean()
            entry.save()
            messages.success(request, "Stundeneintrag gespeichert.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")

        month = request.POST.get("date", "")[:7]  # YYYY-MM
        if month:
            parts = month.split("-")
            return redirect(
                f"/stunden/?year={parts[0]}&month={int(parts[1])}"
            )
        return redirect("timetracking:time_entry_list")


class TimeEntryUpdateView(BetreuerRequiredMixin, View):
    """Update an existing time entry."""

    def get(self, request, pk):
        entry = get_object_or_404(
            TimeEntry.objects.select_related("contract"),
            pk=pk,
            contract__betreuer__user=request.user,
        )
        form = TimeEntryForm(instance=entry, contract=entry.contract)
        if request.htmx:
            html = render_to_string(
                "timetracking/partials/_time_entry_form.html",
                {"form": form, "entry": entry},
                request=request,
            )
            return HttpResponse(html)
        return render(
            request,
            "timetracking/time_entry_edit.html",
            {"form": form, "entry": entry},
        )

    def post(self, request, pk):
        entry = get_object_or_404(
            TimeEntry, pk=pk, contract__betreuer__user=request.user
        )
        # Cannot edit entries that are already linked to a submitted/approved timesheet
        if entry.timesheet and entry.timesheet.status in ("submitted", "approved"):
            messages.error(request, "Eintrag gehoert zu einem eingereichten Nachweis.")
            return redirect("timetracking:time_entry_list")

        form = TimeEntryForm(request.POST, instance=entry, contract=entry.contract)
        if form.is_valid():
            updated_entry = form.save(commit=False)
            # Also block if the new target date falls in a locked month
            locked_timesheet = MonthlyTimesheet.objects.filter(
                contract=updated_entry.contract,
                month=updated_entry.date.month,
                year=updated_entry.date.year,
                status__in=("submitted", "approved"),
            ).first()
            if locked_timesheet:
                messages.error(
                    request,
                    f"Fuer {updated_entry.date.month:02d}/{updated_entry.date.year} "
                    f"wurde bereits ein Stundennachweis eingereicht. Aenderung gesperrt.",
                )
                return redirect(
                    f"/stunden/?year={updated_entry.date.year}&month={updated_entry.date.month}"
                )
            updated_entry.full_clean()
            updated_entry.save()
            entry = updated_entry
            messages.success(request, "Eintrag aktualisiert.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
        return redirect(
            f"/stunden/?year={entry.date.year}&month={entry.date.month}"
        )


class TimeEntryDeleteView(BetreuerRequiredMixin, View):
    """Delete a time entry."""

    def post(self, request, pk):
        entry = get_object_or_404(
            TimeEntry, pk=pk, contract__betreuer__user=request.user
        )
        if entry.timesheet and entry.timesheet.status in ("submitted", "approved"):
            messages.error(request, "Eintrag gehoert zu einem eingereichten Nachweis.")
            return redirect("timetracking:time_entry_list")

        entry_date = entry.date
        entry.delete()
        messages.success(request, "Eintrag geloescht.")
        return redirect(
            f"/stunden/?year={entry_date.year}&month={entry_date.month}"
        )


# ------------------------------------------------------------------
# Betreuer: HTMX helpers
# ------------------------------------------------------------------


class FoerderprogrammeForContractView(BetreuerRequiredMixin, View):
    """
    HTMX endpoint: return <option> elements for the Foerderprogramme
    belonging to a specific contract (owned by the requesting Betreuer).

    GET ?contract=<id>
    """

    def get(self, request):
        contract_id = request.GET.get("contract")
        foerderprogramme = []
        if contract_id:
            try:
                contract = Contract.objects.get(
                    pk=contract_id,
                    betreuer__user=request.user,
                )
                foerderprogramme = list(
                    contract.foerderprogramme.filter(is_active=True)
                )
            except (Contract.DoesNotExist, ValueError):
                pass

        return render(
            request,
            "timetracking/partials/_foerderprogramm_options.html",
            {"foerderprogramme": foerderprogramme},
        )


# ------------------------------------------------------------------
# Betreuer: Timesheet Submission
# ------------------------------------------------------------------


class TimesheetSubmitView(BetreuerRequiredMixin, View):
    """Submit a monthly timesheet for approval."""

    def post(self, request):
        contract_id = request.POST.get("contract")
        try:
            month = int(request.POST.get("month", 0))
            year = int(request.POST.get("year", 0))
        except (ValueError, TypeError):
            messages.error(request, "Ungueltige Monats- oder Jahresangabe.")
            return redirect("timetracking:time_entry_list")

        contract = get_object_or_404(
            Contract, pk=contract_id, betreuer__user=request.user
        )

        # Get or create timesheet
        timesheet, created = MonthlyTimesheet.objects.get_or_create(
            contract=contract,
            month=month,
            year=year,
        )

        try:
            timesheet.submit()
            messages.success(
                request,
                f"Stundennachweis fuer {month:02d}/{year} eingereicht "
                f"({timesheet.total_hours} Std., {timesheet.total_amount} EUR).",
            )
        except ValueError as exc:
            messages.error(request, str(exc))

        return redirect(f"/stunden/?year={year}&month={month}")


# ------------------------------------------------------------------
# Koordinator/Admin: Timesheet Review
# ------------------------------------------------------------------


class TimesheetListView(KoordinatorOrAdminMixin, ListView):
    """List all submitted timesheets for Koordinator/Admin review."""

    template_name = "timetracking/timesheet_list.html"
    context_object_name = "timesheets"
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        qs = MonthlyTimesheet.objects.select_related(
            "contract__betreuer__user",
            "contract__school",
            "contract__activity_type",
        )

        # Koordinator: filter by their schools
        if hasattr(user, "profile") and user.profile.is_koordinator:
            school_ids = user.profile.schools.values_list("pk", flat=True)
            qs = qs.filter(contract__school_id__in=school_ids)

        # Optional status filter
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        return qs.order_by("-year", "-month", "contract__school__code")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["status_choices"] = MonthlyTimesheet.STATUS_CHOICES
        return context


class TimesheetDetailView(KoordinatorOrAdminMixin, TemplateView):
    """Detail view of a single timesheet with its entries."""

    template_name = "timetracking/timesheet_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = MonthlyTimesheet.objects.select_related(
            "contract__betreuer__user",
            "contract__school",
            "contract__activity_type",
        )
        # Koordinator may only see timesheets for their schools
        user = self.request.user
        if hasattr(user, "profile") and user.profile.is_koordinator:
            school_ids = user.profile.schools.values_list("pk", flat=True)
            qs = qs.filter(contract__school_id__in=school_ids)
        timesheet = get_object_or_404(qs, pk=self.kwargs["pk"])
        entries = TimeEntry.objects.filter(
            contract=timesheet.contract,
            date__month=timesheet.month,
            date__year=timesheet.year,
        ).select_related(
            "foerderprogramm",
            "foerderprogramm__kostenstelle",
        ).order_by("date", "start_time")

        context["timesheet"] = timesheet
        context["entries"] = entries
        return context


class TimesheetApproveView(KoordinatorOrAdminMixin, View):
    """
    Genehmigt einen eingereichten Stundennachweis. PDF-Erstellung und
    n8n-Notifications werden per ``on_commit`` an django-q2 uebergeben,
    damit der Koordinator-Request nicht durch WeasyPrint / HTTP-Timeouts
    blockiert wird.
    """

    def post(self, request, pk):
        from django.db import transaction

        qs = MonthlyTimesheet.objects.all()
        # Koordinator may only approve timesheets for their schools
        if hasattr(request.user, "profile") and request.user.profile.is_koordinator:
            school_ids = request.user.profile.schools.values_list("pk", flat=True)
            qs = qs.filter(contract__school_id__in=school_ids)
        timesheet = get_object_or_404(qs, pk=pk)

        try:
            with transaction.atomic():
                timesheet.approve(request.user)
                timesheet_pk = timesheet.pk

                def _schedule_followup():
                    # Darf NIEMALS eine Exception re-raisen -- sonst wird
                    # der bereits committete DB-State inkonsistent mit der
                    # Response und Django-Q kann den Request noch
                    # zuruecksetzen. Alle Fehler werden still geloggt.
                    try:
                        from django_q.tasks import async_task
                        async_task(
                            "apps.timetracking.services.generate_timesheet_pdf_and_notify",
                            timesheet_pk,
                        )
                    except Exception as exc:
                        logger.error(
                            "Could not schedule follow-up for timesheet %s: %s",
                            timesheet_pk,
                            exc,
                            exc_info=True,
                        )

                transaction.on_commit(_schedule_followup)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("timetracking:timesheet_detail", pk=timesheet.pk)

        messages.success(
            request,
            f"Nachweis {timesheet.month:02d}/{timesheet.year} genehmigt. "
            f"Das Abrechnungs-PDF wird im Hintergrund erstellt.",
        )
        return redirect("timetracking:timesheet_detail", pk=timesheet.pk)


class TimesheetRejectView(KoordinatorOrAdminMixin, View):
    """Reject a submitted timesheet."""

    def post(self, request, pk):
        qs = MonthlyTimesheet.objects.all()
        # Koordinator may only reject timesheets for their schools
        if hasattr(request.user, "profile") and request.user.profile.is_koordinator:
            school_ids = request.user.profile.schools.values_list("pk", flat=True)
            qs = qs.filter(contract__school_id__in=school_ids)
        timesheet = get_object_or_404(qs, pk=pk)
        reason = request.POST.get("rejection_reason", "")
        try:
            timesheet.reject(request.user, reason=reason)
            messages.warning(
                request,
                f"Nachweis {timesheet.month:02d}/{timesheet.year} abgelehnt.",
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("timetracking:timesheet_detail", pk=timesheet.pk)


# ------------------------------------------------------------------
# PDF Download
# ------------------------------------------------------------------


class TimesheetPDFDownloadView(LoginRequiredMixin, View):
    """
    Download the generated accounting PDF for a timesheet.

    Access control:
    - Betreuer: only their own timesheets
    - Koordinator: timesheets for their schools
    - Admin: all timesheets
    """

    def get(self, request, pk):
        timesheet = get_object_or_404(
            MonthlyTimesheet.objects.select_related(
                "contract__betreuer__user",
                "contract__school",
            ),
            pk=pk,
        )

        # Access control
        user = request.user
        if not hasattr(user, "profile"):
            raise Http404

        profile = user.profile

        if profile.is_admin:
            pass  # Admin can download all
        elif profile.is_koordinator:
            school_ids = profile.schools.values_list("pk", flat=True)
            if timesheet.contract.school_id not in school_ids:
                raise Http404
        elif profile.is_betreuer:
            betreuer_profile = getattr(user, "betreuer_profile", None)
            if not betreuer_profile or timesheet.contract.betreuer_id != betreuer_profile.pk:
                raise Http404
        else:
            raise Http404

        # Check if PDF exists
        if not timesheet.generated_pdf:
            messages.error(request, "Kein PDF vorhanden fuer diesen Nachweis.")
            return redirect("timetracking:timesheet_detail", pk=timesheet.pk)

        try:
            file_handle = timesheet.generated_pdf.open("rb")
        except (FileNotFoundError, OSError) as exc:
            logger.error(
                "Timesheet %s PDF konnte nicht geoeffnet werden: %s",
                timesheet.pk, exc,
            )
            messages.error(
                request,
                "Die PDF-Datei ist aktuell nicht verfuegbar. "
                "Bitte erneut generieren lassen.",
            )
            return redirect("timetracking:timesheet_detail", pk=timesheet.pk)

        response = FileResponse(
            file_handle,
            content_type="application/pdf",
        )
        filename = (
            f"stundennachweis_"
            f"{timesheet.contract.contract_number}_"
            f"{timesheet.year}{timesheet.month:02d}.pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
