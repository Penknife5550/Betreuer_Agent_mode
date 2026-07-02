"""
Authentifizierungs-Backend fuer Login per E-Mail.

Betreuer sind ueberwiegend Schueler; ein kryptischer, automatisch erzeugter
Benutzername (E-Mail-Prefix) ist fuer sie nicht auffindbar. Dieses Backend
erlaubt zusaetzlich zum Standard-Username-Login die Anmeldung mit der
E-Mail-Adresse. Das Username-Login (ModelBackend) bleibt fuer Admins bestehen.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Anmeldung per E-Mail (case-insensitive). Bei mehrdeutiger E-Mail
    (mehrere Nutzer mit derselben Adresse) wird bewusst verweigert."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username or password is None:
            return None
        try:
            user = UserModel.objects.get(email__iexact=username.strip())
        except UserModel.DoesNotExist:
            # Timing-Angriffe abschwaechen (gleicher Aufwand wie bei Treffer).
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None  # mehrdeutig -> nicht anmelden
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
