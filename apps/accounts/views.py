import logging

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from apps.core.constants import INPUT_CSS
from apps.documents.services import mask_iban

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    """
    Custom login view that redirects users to their role-specific dashboard
    after successful authentication.

    Redirect targets:
        - admin       -> /admin-dashboard/
        - koordinator -> /koordinator-dashboard/
        - betreuer    -> /betreuer-dashboard/

    Users without a profile (e.g. superusers created via createsuperuser)
    are sent to /admin-dashboard/ as a sensible fallback.

    Bug-fix: We override get_success_url() instead of get_redirect_url().
    get_redirect_url() is called on both GET (page render) and POST (form
    submit), so overriding it caused AnonymousUser to be checked during the
    GET request, which embedded "/admin-dashboard/" as the hidden ``next``
    value in the form – causing every non-admin user to be redirected there
    after login.  get_success_url() is only called after a successful login.
    """

    template_name = "registration/login.html"

    def form_valid(self, form):
        """Rotate session key after successful login (prevent session fixation)."""
        response = super().form_valid(form)
        self.request.session.cycle_key()
        return response

    def get_success_url(self):
        """
        Return the URL to redirect to after a successful login.
        Respects an explicit ``?next=`` parameter when present and safe;
        otherwise falls back to the role-based dashboard URL.
        """
        # Honour an explicit, safe redirect target (e.g. ?next=/profil/)
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return self._get_dashboard_url_for_user(self.request.user)

    def _get_dashboard_url_for_user(self, user):
        """Determine the correct dashboard URL based on the user's profile role."""
        if not hasattr(user, "profile"):
            # Superuser without profile -> admin dashboard
            logger.info(
                "User '%s' has no profile – redirecting to admin dashboard.",
                user.username,
            )
            return "/admin-dashboard/"

        role = user.profile.role
        if role == "admin":
            return "/admin-dashboard/"
        elif role == "koordinator":
            return "/koordinator-dashboard/"
        elif role == "betreuer":
            return "/betreuer-dashboard/"

        # Unknown role – fallback
        logger.warning(
            "User '%s' has unknown role '%s' – redirecting to /login/.",
            user.username,
            role,
        )
        return "/login/"


class PasswordResetRequestForm(forms.Form):
    """'Passwort vergessen' -- der Nutzer gibt nur seine E-Mail ein."""

    email = forms.EmailField(
        label="E-Mail-Adresse",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CSS, "placeholder": "name@beispiel.de",
                   "autocomplete": "email"}
        ),
    )


class PasswordResetRequestView(FormView):
    """
    Self-Service 'Passwort vergessen': verschickt einen Reset-Link per SMTP
    (send_credo_email, gleiche Infrastruktur wie die uebrigen Mails).

    Kein User-Enumeration: es wird IMMER die gleiche Bestaetigungsseite
    angezeigt, egal ob die E-Mail existiert.
    """

    template_name = "accounts/password_reset_request.html"
    form_class = PasswordResetRequestForm
    success_url = reverse_lazy("accounts:password_reset_sent")

    def form_valid(self, form):
        from apps.core.email import build_site_url, send_credo_email

        email = form.cleaned_data["email"].strip()
        User = get_user_model()
        for user in User.objects.filter(email__iexact=email, is_active=True):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = build_site_url(
                reverse("accounts:password_reset_confirm",
                        kwargs={"uidb64": uid, "token": token})
            )
            name = user.get_full_name().strip()
            send_credo_email(
                to=user.email,
                kind="password_reset",
                subject="Passwort zuruecksetzen - BetreuerApp",
                greeting=f"Guten Tag {name}," if name else "Guten Tag,",
                paragraphs=[
                    "Sie haben angefordert, Ihr Passwort zurueckzusetzen.",
                    "Klicken Sie auf den Button, um ein neues Passwort zu vergeben.",
                ],
                cta_label="Neues Passwort festlegen",
                cta_url=link,
                outro_paragraphs=[
                    "Falls Sie das nicht angefordert haben, koennen Sie diese "
                    "E-Mail ignorieren. Der Link ist 14 Tage gueltig.",
                ],
            )
        return super().form_valid(form)


@require_POST
@login_required
def logout_view(request):
    """Logout via POST (CSRF-geschuetzt). Verhindert Forced-Logout durch
    Prefetcher/Image-Tags. Django 5+ erlaubt nur noch POST fuer Logout."""
    logout(request)
    return redirect("accounts:login")


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    User profile page showing personal data.

    Betreuers see their full profile (address, bank, freibetrag).
    Other roles see basic account info.
    """

    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if hasattr(user, "profile") and user.profile.is_betreuer:
            betreuer_profile = getattr(user, "betreuer_profile", None)
            if betreuer_profile:
                context["betreuer_profile"] = betreuer_profile
                context["iban_masked"] = mask_iban(betreuer_profile.iban)

        return context


class ProfileEditView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Profile edit form – only accessible to Betreuer users.

    Allows editing: address, phone, bank details, freibetrag declaration.
    Changes to BetreuerProfile are automatically audit-logged.
    """

    template_name = "accounts/profile_edit.html"
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return (
            hasattr(user, "profile")
            and user.profile.is_betreuer
            and hasattr(user, "betreuer_profile")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            from apps.accounts.forms import BetreuerProfileEditForm

            context["form"] = BetreuerProfileEditForm(
                betreuer_profile=self.request.user.betreuer_profile,
                user_profile=self.request.user.profile,
            )
        return context

    def post(self, request, *args, **kwargs):
        from apps.accounts.forms import BetreuerProfileEditForm

        form = BetreuerProfileEditForm(
            request.POST,
            betreuer_profile=request.user.betreuer_profile,
            user_profile=request.user.profile,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profil erfolgreich aktualisiert.")
            return redirect("accounts:profile")
        return self.render_to_response(self.get_context_data(form=form))


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    Password change view with Tailwind-styled template.

    Available to all authenticated users (all roles).
    """

    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Passwort erfolgreich geaendert.")
        return super().form_valid(form)
