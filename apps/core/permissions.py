"""
Zentralisierte Berechtigungs-Helper fuer das gesamte Projekt.

Ersetzt duplizierte ``KoordinatorOrAdminMixin``-Implementierungen in
contracts, timetracking und reports sowie die ``_koordinator_has_access_to_betreuer``
Helper-Funktion in documents.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404


def has_admin_role(user):
    """True fuer Superuser oder UserProfile.is_admin."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return hasattr(user, "profile") and user.profile.is_admin


def has_koordinator_role(user):
    """True fuer Superuser, Admin oder UserProfile.is_koordinator."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, "profile"):
        return False
    return user.profile.is_admin or user.profile.is_koordinator


def koordinator_has_access_to_betreuer(user, betreuer_profile):
    """
    True wenn der Benutzer Admin ist oder Koordinator einer Schule, an der
    der Betreuer einen Vertrag hat. Dient als IDOR-Schutz ueberall, wo
    Koordinatoren Betreuer-bezogene Aktionen ausfuehren.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, "profile"):
        return False
    if user.profile.is_admin:
        return True
    if not user.profile.is_koordinator:
        return False
    koordinator_school_ids = set(user.profile.schools.values_list("id", flat=True))
    betreuer_school_ids = set(betreuer_profile.contracts.values_list("school_id", flat=True))
    return bool(koordinator_school_ids & betreuer_school_ids)


def require_scope_access(user, betreuer_profile):
    """
    Raise Http404 wenn Benutzer keinen Zugriff auf den Betreuer hat.
    Bewusst Http404 statt 403, um Existenz fremder Datensaetze nicht zu verraten.
    """
    if not koordinator_has_access_to_betreuer(user, betreuer_profile):
        raise Http404


class KoordinatorOrAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin fuer Views, die nur von Koordinatoren oder Admins aufgerufen
    werden duerfen. Zusaetzlicher Scope-Check (Schule) muss in der View
    pro Objekt erfolgen -- dieser Mixin prueft nur die Rolle.
    """

    raise_exception = True

    def test_func(self):
        return has_koordinator_role(self.request.user)


class KoordinatorScopedMixin(KoordinatorOrAdminMixin):
    """
    Mixin fuer Views, die zusaetzlich zum Rollen-Check automatisch
    den Scope-Check durchfuehren: Koordinatoren duerfen nur auf
    ``BetreuerProfile``-Objekte zugreifen, die an einer ihrer Schulen
    einen Vertrag haben. Admins/Superuser bleiben uneingeschraenkt.

    Muss ``get_object()`` aufrufen koennen -- typischerweise
    kombiniert mit ``DetailView`` / ``UpdateView`` / ``DeleteView``.
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        # Lokaler Import, um zirkulaere Modell-Imports zu vermeiden.
        from apps.contracts.models import BetreuerProfile

        if isinstance(obj, BetreuerProfile):
            require_scope_access(self.request.user, obj)
        elif hasattr(obj, "betreuer"):
            require_scope_access(self.request.user, obj.betreuer)
        return obj


class AdminOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin fuer Views, die nur von Admins (oder Superusern) aufgerufen werden duerfen."""

    raise_exception = True

    def test_func(self):
        return has_admin_role(self.request.user)


class BetreuerOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin fuer Views, die nur von Betreuern aufgerufen werden duerfen."""

    raise_exception = True

    def test_func(self):
        user = self.request.user
        return hasattr(user, "profile") and user.profile.is_betreuer
