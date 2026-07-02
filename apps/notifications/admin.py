"""
Admin fuer die Webhook-Konfiguration.
"""

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from apps.notifications.models import (
    EmailLog,
    InboundToken,
    NotificationLog,
    SmtpConfig,
    WebhookEndpoint,
)


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "url",
        "is_active",
        "timeout_seconds",
        "updated_at",
    )
    list_filter = ("is_active", "event_type")
    search_fields = ("event_type", "url", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("event_type", "url", "is_active", "description"),
        }),
        ("Authentifizierung", {
            "fields": ("auth_header_name", "auth_header_value"),
            "description": (
                "Optionaler Auth-Header, der mit jedem Request mitgesendet wird. "
                "Beispiel: Name 'Authorization', Wert 'Bearer abc123...'."
            ),
        }),
        ("Verbindung", {
            "fields": ("timeout_seconds",),
        }),
        ("Audit", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(InboundToken)
class InboundTokenAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_active", "updated_at")

    def has_add_permission(self, request):
        # Singleton: nur ein Eintrag erlaubt
        return not InboundToken.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Loeschen verhindert Auth-Bruch -- bitte nur Token aendern oder deaktivieren
        return False


class SmtpConfigAdminForm(forms.ModelForm):
    """Passwort maskiert eingeben; leer lassen = bestehendes behalten."""

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="SMTP-Passwort. Leer lassen = bestehendes Passwort behalten. "
        "Wird verschluesselt gespeichert.",
    )

    class Meta:
        model = SmtpConfig
        fields = "__all__"

    def clean_password(self):
        pw = self.cleaned_data.get("password")
        if not pw:
            if self.instance and self.instance.pk:
                return self.instance.password  # bestehendes behalten
            return None
        return pw


@admin.register(SmtpConfig)
class SmtpConfigAdmin(admin.ModelAdmin):
    """Singleton -- SMTP-Zugangsdaten und Rollen-Adressen fuer den Direktversand."""

    form = SmtpConfigAdminForm
    change_form_template = "admin/notifications/smtpconfig_change_form.html"
    list_display = ("host", "port", "is_active", "from_email", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Server", {
            "fields": ("host", "port", "use_tls", "use_ssl", "username", "password"),
        }),
        ("Absender", {
            "fields": ("from_email", "from_name"),
        }),
        ("Rollen-Empfaenger", {
            "fields": ("admin_email", "buchhaltung_email"),
            "description": "Adressen fuer interne bzw. Buchhaltungs-Benachrichtigungen. "
            "Leer = Fallback auf DEFAULT_FROM_EMAIL.",
        }),
        ("Aktivierung", {
            "fields": ("is_active", "updated_at"),
        }),
    )

    def has_add_permission(self, request):
        # Singleton: nur ein Eintrag erlaubt.
        return not SmtpConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    # --- Testmail-Funktion ---------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "testmail/",
                self.admin_site.admin_view(self.test_email_view),
                name="notifications_smtpconfig_testmail",
            ),
        ]
        return custom + urls

    def test_email_view(self, request):
        """Sendet eine Testmail an eine eingegebene Adresse und zeigt das
        Ergebnis (inkl. exaktem SMTP-Fehler)."""
        from apps.core.email import send_test_email

        if request.method == "POST":
            to = request.POST.get("test_email", "").strip()
            ok, detail = send_test_email(to)
            if ok:
                self.message_user(request, detail, level=messages.SUCCESS)
                return redirect("admin:notifications_smtpconfig_testmail")
            self.message_user(request, detail, level=messages.ERROR)

        context = {
            **self.admin_site.each_context(request),
            "title": "SMTP-Testmail senden",
            "opts": self.model._meta,
            "prefill": (SmtpConfig.objects.filter(pk=1).first().admin_email
                        if SmtpConfig.objects.filter(pk=1).exists() else ""),
        }
        return render(request, "admin/notifications/smtpconfig_testmail.html", context)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Read-only Einsicht in direkt versendete E-Mails."""

    list_display = ("created_at", "recipient", "kind", "status", "subject")
    list_filter = ("status", "kind", "created_at")
    search_fields = ("recipient", "subject", "detail")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "recipient", "subject", "kind", "status", "detail")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Read-only Einsicht in gesendete/fehlgeschlagene Benachrichtigungen."""

    list_display = (
        "created_at",
        "event_type",
        "status",
        "http_status",
        "endpoint_url",
    )
    list_filter = ("status", "event_type", "created_at")
    search_fields = ("event_type", "endpoint_url", "error")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at",
        "event_type",
        "status",
        "http_status",
        "endpoint_url",
        "payload",
        "error",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Nur ansehen, nicht editieren.
        return False

    def has_delete_permission(self, request, obj=None):
        # Aufraeumen des Logs bleibt Admins erlaubt.
        return True
