"""
Dashboard views with real data.

AdminDashboardView: Full system overview with KPIs.
KoordinatorDashboardView: Scoped to assigned schools.
BetreuerDashboardView: Personal overview with documents, hours, freibetrag.
"""

from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.views.generic import TemplateView

from apps.contracts.models import BetreuerProfile, Contract
from apps.documents.models import Document
from apps.freibetrag.services import get_freibetrag_status
from apps.schools.services import get_foerderprogramm_budget_status
from apps.timetracking.models import MonthlyTimesheet, TimeEntry


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard for Admin/HR users with full system overview.
    Accessible only to users with the 'admin' role.
    """

    template_name = "dashboards/admin_dashboard.html"
    raise_exception = True

    def test_func(self):
        user = self.request.user
        # Superusers without a profile are also granted access
        if user.is_superuser and not hasattr(user, "profile"):
            return True
        return hasattr(user, "profile") and user.profile.is_admin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.schools.models import School

        context["betreuer_count"] = BetreuerProfile.objects.filter(
            onboarding_status="active"
        ).count()
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

        # Count betreuers approaching or exceeding Freibetrag limit
        active_betreuers = BetreuerProfile.objects.filter(onboarding_status="active")
        warning_count = 0
        for bp in active_betreuers:
            status = get_freibetrag_status(bp)
            if status["warning_level"]:
                warning_count += 1
        context["freibetrag_warnings"] = warning_count

        # Foerderprogramm budget statuses (only programmes with a budget set)
        from apps.schools.models import Foerderprogramm
        fps_with_budget = Foerderprogramm.objects.filter(
            budget__isnull=False, is_active=True
        ).select_related("school_year", "kostenstelle").order_by("school_year__start_date", "name")
        fp_budget_statuses = [
            {"foerderprogramm": fp, "status": get_foerderprogramm_budget_status(fp)}
            for fp in fps_with_budget
        ]
        context["fp_budget_statuses"] = fp_budget_statuses
        context["fp_budget_warning_count"] = sum(
            1 for x in fp_budget_statuses if x["status"] and x["status"]["warning_level"]
        )

        return context


class KoordinatorDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard for Koordinator users scoped to their assigned schools.
    Accessible only to users with the 'koordinator' role.
    """

    template_name = "dashboards/koordinator_dashboard.html"
    raise_exception = True

    def test_func(self):
        return hasattr(self.request.user, "profile") and self.request.user.profile.is_koordinator

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        schools = profile.schools.all()
        school_ids = schools.values_list("pk", flat=True)
        context["schools"] = schools
        context["betreuer_count"] = BetreuerProfile.objects.filter(
            contracts__school_id__in=school_ids
        ).distinct().count()
        context["pending_timesheets"] = MonthlyTimesheet.objects.filter(
            status="submitted",
            contract__school_id__in=school_ids,
        ).count()
        context["school_count"] = schools.count()
        context["documents_pending"] = Document.objects.filter(
            status="uploaded",
            contract__school_id__in=school_ids,
        ).count()
        context["contract_count"] = Contract.objects.filter(
            school_id__in=school_ids,
        ).exclude(status="terminated").count()

        # Freibetrag warnings scoped to koordinator's schools
        betreuer_profiles = BetreuerProfile.objects.filter(
            contracts__school_id__in=school_ids,
            onboarding_status="active",
        ).distinct()
        freibetrag_warning_count = 0
        for bp in betreuer_profiles:
            status = get_freibetrag_status(bp)
            if status["warning_level"]:
                freibetrag_warning_count += 1
        context["freibetrag_warning_count"] = freibetrag_warning_count

        # Foerderprogramm budget statuses scoped to koordinator's schools
        from apps.schools.models import Foerderprogramm
        fps_with_budget = Foerderprogramm.objects.filter(
            budget__isnull=False,
            is_active=True,
            contracts__school_id__in=school_ids,
        ).select_related("school_year", "kostenstelle").distinct().order_by("school_year__start_date", "name")
        fp_budget_statuses = [
            {"foerderprogramm": fp, "status": get_foerderprogramm_budget_status(fp)}
            for fp in fps_with_budget
        ]
        context["fp_budget_statuses"] = fp_budget_statuses
        context["fp_budget_warning_count"] = sum(
            1 for x in fp_budget_statuses if x["status"] and x["status"]["warning_level"]
        )

        return context


class BetreuerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard for Betreuer users showing their personal overview.
    Accessible only to users with the 'betreuer' role.
    """

    template_name = "dashboards/betreuer_dashboard.html"
    raise_exception = True

    def test_func(self):
        return hasattr(self.request.user, "profile") and self.request.user.profile.is_betreuer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        betreuer_profile = getattr(user, "betreuer_profile", None)

        if not betreuer_profile:
            return context

        context["betreuer_profile"] = betreuer_profile

        today = date.today()
        current_month_minutes = TimeEntry.objects.filter(
            contract__betreuer=betreuer_profile,
            date__month=today.month,
            date__year=today.year,
        ).aggregate(total=Sum("duration_minutes"))["total"] or 0
        context["current_hours"] = round(current_month_minutes / 60, 1)

        freibetrag = get_freibetrag_status(betreuer_profile)
        context["freibetrag"] = freibetrag

        documents = Document.objects.filter(
            betreuer=betreuer_profile
        ).select_related("requirement")
        context["documents"] = documents
        context["documents_total"] = documents.count()
        context["documents_pending"] = documents.exclude(
            status="verified"
        ).count()

        contracts = Contract.objects.filter(
            betreuer=betreuer_profile
        ).exclude(status="terminated").select_related(
            "school", "activity_type",
        ).prefetch_related("foerderprogramme")
        context["contracts"] = contracts
        context["contract_count"] = contracts.count()

        context["open_timesheets"] = MonthlyTimesheet.objects.filter(
            contract__betreuer=betreuer_profile,
            status__in=["draft", "rejected"],
        ).count()

        # Foerderprogramm budget statuses for the betreuer's active contracts
        from apps.schools.models import Foerderprogramm
        _active_statuses = ["draft", "generated", "sent", "signed", "active"]
        fps_with_budget = Foerderprogramm.objects.filter(
            contracts__betreuer=betreuer_profile,
            contracts__status__in=_active_statuses,
            budget__isnull=False,
            is_active=True,
        ).select_related("school_year", "kostenstelle").distinct().order_by("name")
        context["foerderprogramm_budgets"] = [
            {"foerderprogramm": fp, "status": get_foerderprogramm_budget_status(fp)}
            for fp in fps_with_budget
        ]

        return context
