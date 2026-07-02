from django.contrib.auth.views import PasswordResetCompleteView, PasswordResetConfirmView
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from apps.accounts.views import (
    CustomLoginView,
    CustomPasswordChangeView,
    PasswordResetRequestView,
    ProfileEditView,
    ProfileView,
    logout_view,
)

app_name = "accounts"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    # Self-Service "Passwort vergessen"
    path("passwort-vergessen/", PasswordResetRequestView.as_view(), name="password_reset"),
    path(
        "passwort-vergessen/gesendet/",
        TemplateView.as_view(template_name="accounts/password_reset_sent.html"),
        name="password_reset_sent",
    ),
    path("profil/", ProfileView.as_view(), name="profile"),
    path("profil/bearbeiten/", ProfileEditView.as_view(), name="profile_edit"),
    path("profil/passwort-aendern/", CustomPasswordChangeView.as_view(), name="password_change"),
    # Password setup for new Betreuer (link is generated at registration and sent via N8N)
    path(
        "accounts/passwort-setzen/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            success_url=reverse_lazy("accounts:password_reset_complete"),
            template_name="accounts/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/passwort-gesetzt/",
        PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
