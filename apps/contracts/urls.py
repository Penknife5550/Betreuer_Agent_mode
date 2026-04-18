from django.urls import path

from apps.contracts.views import (
    ActivityTypeLookupView,
    ApprovalView,
    BetreuerActivateView,
    BetreuerDetailView,
    BetreuerListView,
    BetreuerReviewView,
    BetreuerUpdateAccountingView,
    CreateRegistrationLinkView,
    FoerderprogrammLookupView,
    HashCheckView,
    PublicRegistrationView,
    RateLookupView,
    RegistrationLinkListView,
    RegistrationSuccessView,
    RegistrationView,
)

app_name = "contracts"

urlpatterns = [
    # --- Public registration (no login required) ---
    path(
        "registrierung/",
        PublicRegistrationView.as_view(),
        name="public_registration",
    ),
    path(
        "registrierung/erfolg/",
        RegistrationSuccessView.as_view(),
        name="registration_success",
    ),
    # Oeffentliche HTMX-Endpoints fuer das Registrierungsformular.
    # Bewusst unter /registrierung/htmx/ gemountet, damit die
    # LoginRequiredMiddleware-EXEMPT_URLS praezise passt und keine
    # versteckten /api/-Endpoints auto-exempt werden.
    path(
        "registrierung/htmx/rate-lookup/",
        RateLookupView.as_view(),
        name="rate_lookup",
    ),
    path(
        "registrierung/htmx/foerderprogramm-lookup/",
        FoerderprogrammLookupView.as_view(),
        name="foerderprogramm_lookup",
    ),
    path(
        "registrierung/htmx/activity-type-lookup/",
        ActivityTypeLookupView.as_view(),
        name="activity_type_lookup",
    ),
    path(
        "registrierung/htmx/hash-check/",
        HashCheckView.as_view(),
        name="hash_check",
    ),
    path(
        "registrierung/<uuid:token>/",
        RegistrationView.as_view(),
        name="token_registration",
    ),
    # --- Koordinator: Registration links ---
    path(
        "koordinator/registrierungslink-erstellen/",
        CreateRegistrationLinkView.as_view(),
        name="create_registration_link",
    ),
    path(
        "koordinator/registrierungslinks/",
        RegistrationLinkListView.as_view(),
        name="registration_link_list",
    ),
    # --- Betreuer management ---
    path(
        "betreuer-liste/",
        BetreuerListView.as_view(),
        name="betreuer_list",
    ),
    path(
        "betreuer/<int:pk>/",
        BetreuerDetailView.as_view(),
        name="betreuer_detail",
    ),
    path(
        "betreuer/<int:pk>/pruefen/",
        BetreuerReviewView.as_view(),
        name="betreuer_review",
    ),
    path(
        "betreuer/<int:pk>/aktivieren/",
        BetreuerActivateView.as_view(),
        name="betreuer_activate",
    ),
    path(
        "betreuer/<int:pk>/buchhaltung/",
        BetreuerUpdateAccountingView.as_view(),
        name="betreuer_update_accounting",
    ),
    # --- Koordinator approval (V2) ---
    path(
        "betreuer/<int:pk>/genehmigen/",
        ApprovalView.as_view(),
        name="betreuer_approve",
    ),
]
