"""
Dashboard views (Admin / Koordinator / Betreuer).

Performance-Invariante: keine O(n)-Python-Loops ueber DB-Aggregate.
Freibetrag-Warnungen werden per ``count_freibetrag_warnings`` in einer
einzigen aggregierten Query gezaehlt. Foerderprogramm-Budgets werden per
``get_budget_statuses_bulk`` ermittelt.
"""

from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q, Sum
from django.views.generic import TemplateView

from apps.contracts.models import BetreuerProfile, Contract
from apps.documents.models import Document
from apps.freibetrag.services import count_freibetrag_warnings, get_freibetrag_status
from apps.schools.services import get_budget_statuses_bulk
from apps.timetracking.models import MonthlyTimesheet, TimeEntry


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Admin-Dashboard mit Systemweiten KPIs."""

    template_name = "dashboards/admin_dashboard.html"
    raise_exception = True

    def test_func(self):
        user = self.request.user
        if user.is_superuser and not hasattr(user, "profile"):
            return True
        return hasattr(user, "profile") and user.profile.is_admin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.schools.models import Foerderprogramm, School

        # Kombinierte Count-Query fuer die Stammdaten-KPIs
        betreuer_aggregate = BetreuerProfile.objects.aggregate(
            active=Count("id", filter=Q(onboarding_status="active")),
        )
        context["betreuer_count"] = betreuer_aggregate["active"]
        context["school_count"] = School.objects.filter(is_active=True).count()
        context["pending_timesheets"] = MonthlyTimesheet.objects.filter(
            status="submitted"
        ).count()
        context["contract_count"] = Contract.objects.exclude(
            status="terminated"
        ).count()
        context["expiring_documents"] = Document.objects.filter(
            status="sent"
        ).count()

        # Freibetrag-Warnungen: 1 aggregierte Query statt Python-Loop
        active_betreuers = BetreuerProfile.objects.filter(onboarding_status="active")
        context["freibetrag_warnings"] = count_freibetrag_warnings(active_betreuers)

        # Foerderprogramm-Budgets: Bulk-Status
        fps_with_budget = (
            Foerderprogramm.objects
            .filter(budget__isnull=False, is_active=True)
            .select_related("school_year", "kostenstelle")
            .order_by("school_year__start_date", "name")
        )
        fp_budget_statuses = get_budget_statuses_bulk(fps_with_budget)
        context["fp_budget_statuses"] = fp_budget_statuses
        context["fp_budget_warning_count"] = sum(
            1 for x in fp_budget_statuses if x["status"] and x["status"]["warning_level"]
        )
        return context


class KoordinatorDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Koordinator-Dashboard, gescoped auf die zugewiesenen Schulen."""

    template_name = "dashboards/koordinator_dashboard.html"
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return hasattr(user, "profile") and user.profile.is_koordinator

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.schools.models import Foerderprogramm

        profile = self.request.user.profile
        schools = profile.schools.all()
        school_ids = list(schools.values_list("pk", flat=True))
        context["schools"] = schools
        context["school_count"] = schools.count()

        context["betreuer_count"] = (
            BetreuerProfile.objects
            .filter(contracts__school_id__in=school_ids)
            .distinct()
            .count()
        )
        context["pending_timesheets"] = MonthlyTimesheet.objects.filter(
            status="submitted",
            contract__school_id__in=school_ids,
        ).count()
        context["documents_pending"] = Document.objects.filter(
            status="uploaded",
            contract__school_id__in=school_ids,
        ).count()
        context["contract_count"] = (
            Contract.objects
            .filter(school_id__in=school_ids)
            .exclude(status="terminated")
            .count()
        )

        betreuer_profiles = (
            BetreuerProfile.objects
            .filter(
                contracts__school_id__in=school_ids,
                onboarding_status="active",
            )
            .distinct()
        )
        context["freibetrag_warning_count"] = count_freibetrag_warnings(betreuer_profiles)

        fps_with_budget = (
            Foerderprogramm.objects
            .filter(
                budget__isnull=False,
                is_active=True,
                contracts__school_id__in=school_ids,
            )
            .select_related("school_year", "kostenstelle")
            .distinct()
            .order_by("school_year__start_date", "name")
        )
        fp_budget_statuses = get_budget_statuses_bulk(fps_with_budget)
        context["fp_budget_statuses"] = fp_budget_statuses
        context["fp_budget_warning_count"] = sum(
            1 for x in fp_budget_statuses if x["status"] and x["status"]["warning_level"]
        )
        return context


class BetreuerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Persoenliches Dashboard des Betreuers."""

    template_name = "dashboards/betreuer_dashboard.html"
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return hasattr(user, "profile") and user.profile.is_betreuer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        betreuer_profile = getattr(user, "betreuer_profile", None)
        if not betreuer_profile:
            return context

        context["betreuer_profile"] = betreuer_profile

        today = date.today()
        # Datumsbereich statt date__month/year -> nutzt Index
        first_of_month = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        current_month_minutes = TimeEntry.objects.filter(
            contract__betreuer=betreuer_profile,
            date__gte=first_of_month,
            date__lt=next_month,
        ).aggregate(total=Sum("duration_minutes"))["total"] or 0
        context["current_hours"] = round(current_month_minutes / 60, 1)

        context["freibetrag"] = get_freibetrag_status(betreuer_profile)

        documents = Document.objects.filter(
            betreuer=betreuer_profile
        ).select_related("requirement")
        context["documents"] = documents
        context["documents_total"] = documents.count()
        context["documents_pending"] = documents.exclude(
            status="verified"
        ).count()

        contracts = (
            Contract.objects
            .filter(betreuer=betreuer_profile)
            .exclude(status="terminated")
            .select_related("school", "activity_type")
            .prefetch_related("foerderprogramme")
        )
        context["contracts"] = contracts
        context["contract_count"] = contracts.count()

        context["open_timesheets"] = MonthlyTimesheet.objects.filter(
            contract__betreuer=betreuer_profile,
            status__in=["draft", "rejected"],
        ).count()

        from apps.schools.models import Foerderprogramm

        _active_statuses = ["draft", "generated", "sent", "signed", "active"]
        fps_with_budget = (
            Foerderprogramm.objects
            .filter(
                contracts__betreuer=betreuer_profile,
                contracts__status__in=_active_statuses,
                budget__isnull=False,
                is_active=True,
            )
            .select_related("school_year", "kostenstelle")
            .distinct()
            .order_by("name")
        )
        context["foerderprogramm_budgets"] = get_budget_statuses_bulk(fps_with_budget)
        return context
