"""
Tests for the accounts app.

Covers:
- Login page accessibility
- Login with valid / invalid credentials
- Role-based redirect after login (admin, koordinator, betreuer)
- Logout redirect
- Unauthenticated access redirect
- Profile view (with betreuer data)
- Profile edit (form, validation, audit log)
- Password change
"""

import pytest
from django.test import Client

from apps.core.models import AuditLog


# ---------------------------------------------------------------------------
# Login page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_login_page_accessible():
    """GET /login/ should return HTTP 200."""
    client = Client()
    response = client.get('/login/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_valid_credentials(admin_user):
    """POST /login/ with valid credentials should redirect (302)."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testadmin',
        'password': 'testpass123!',
    })
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_invalid_credentials():
    """POST /login/ with invalid credentials should stay on login page (200) with form errors."""
    client = Client()
    response = client.post('/login/', {
        'username': 'nonexistent',
        'password': 'wrongpass',
    })
    # Django LoginView returns 200 with form errors on failed login
    assert response.status_code == 200
    assert response.context['form'].errors


# ---------------------------------------------------------------------------
# Role-based redirect after login
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_redirected_to_admin_dashboard(admin_user):
    """Admin user should be redirected to /admin-dashboard/ after login."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testadmin',
        'password': 'testpass123!',
    })
    assert response.status_code == 302
    assert response.url == '/admin-dashboard/'


@pytest.mark.django_db
def test_koordinator_redirected_to_koordinator_dashboard(koordinator_user):
    """Koordinator user should be redirected to /koordinator-dashboard/ after login."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testkoord',
        'password': 'testpass123!',
    })
    assert response.status_code == 302
    assert response.url == '/koordinator-dashboard/'


@pytest.mark.django_db
def test_betreuer_redirected_to_betreuer_dashboard(betreuer_user):
    """Betreuer user should be redirected to /betreuer-dashboard/ after login."""
    client = Client()
    response = client.post('/login/', {
        'username': 'testbetreuer',
        'password': 'testpass123!',
    })
    assert response.status_code == 302
    assert response.url == '/betreuer-dashboard/'


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_logout_redirects_to_login(admin_user):
    """GET /logout/ should log the user out and redirect to /login/."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/logout/')
    assert response.status_code == 302
    assert '/login/' in response.url


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_redirected_to_login():
    """GET / (root) by an unauthenticated user should redirect to /login/."""
    client = Client()
    response = client.get('/')
    assert response.status_code == 302
    assert '/login/' in response.url


# ---------------------------------------------------------------------------
# Profile view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_page_accessible(betreuer_user):
    """Betreuer should see their profile page."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_page_shows_betreuer_data(betreuer_user, betreuer_profile):
    """Profile page should show betreuer-specific data (address, masked IBAN)."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/')
    assert response.status_code == 200
    assert "betreuer_profile" in response.context
    assert "iban_masked" in response.context


@pytest.mark.django_db
def test_profile_page_admin_no_betreuer_data(admin_user):
    """Admin profile page should not have betreuer_profile in context."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/profil/')
    assert response.status_code == 200
    assert "betreuer_profile" not in response.context


# ---------------------------------------------------------------------------
# Profile edit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_edit_betreuer_can_access(betreuer_user, betreuer_profile):
    """Betreuer should access profile edit page (GET 200)."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_profile_edit_koordinator_forbidden(koordinator_user):
    """Koordinator should get 403 on profile edit page."""
    client = Client()
    client.force_login(koordinator_user)
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_edit_admin_forbidden(admin_user):
    """Admin should get 403 on profile edit page."""
    client = Client()
    client.force_login(admin_user)
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_profile_edit_unauthenticated_redirect():
    """Unauthenticated user should be redirected to login."""
    client = Client()
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_profile_edit_valid_submission(betreuer_user, betreuer_profile):
    """Valid form submission should update BetreuerProfile and phone."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/bearbeiten/', {
        'street': 'Neue Strasse',
        'house_number': '42',
        'plz': '32427',
        'city': 'Minden',
        'phone': '0571 99999',
        'kontoinhaber': 'Dimitri Riesen',
        'iban': 'DE89 3704 0044 0532 0130 00',
        'bic': 'COBADEFFXXX',
        'freibetrag_used_elsewhere': '',
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })
    assert response.status_code == 302
    assert response.url == '/profil/'

    # Verify BetreuerProfile updated
    betreuer_profile.refresh_from_db()
    assert betreuer_profile.street == 'Neue Strasse'
    assert betreuer_profile.house_number == '42'
    assert betreuer_profile.plz == '32427'

    # Verify UserProfile.phone updated
    betreuer_user.profile.refresh_from_db()
    assert betreuer_user.profile.phone == '0571 99999'


@pytest.mark.django_db
def test_profile_edit_iban_validation(betreuer_user, betreuer_profile):
    """Invalid IBAN should be rejected."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/bearbeiten/', {
        'street': 'Teststr.',
        'house_number': '1',
        'plz': '32425',
        'city': 'Minden',
        'phone': '',
        'kontoinhaber': 'Test',
        'iban': 'INVALID',
        'bic': '',
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })
    assert response.status_code == 200  # Form re-rendered with errors
    assert response.context["form"].errors.get("iban")


@pytest.mark.django_db
def test_profile_edit_audit_log_created(betreuer_user, betreuer_profile):
    """Changing phone should create an AuditLog entry for UserProfile."""
    client = Client()
    client.force_login(betreuer_user)
    client.post('/profil/bearbeiten/', {
        'street': betreuer_profile.street,
        'house_number': betreuer_profile.house_number,
        'plz': betreuer_profile.plz,
        'city': betreuer_profile.city,
        'phone': '0571 NEW',
        'kontoinhaber': betreuer_profile.kontoinhaber,
        'iban': betreuer_profile.iban,
        'bic': betreuer_profile.bic,
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })

    # Check AuditLog for UserProfile phone change
    log = AuditLog.objects.filter(
        model_name="UserProfile",
        action="update",
    ).first()
    assert log is not None
    assert log.changes["phone"]["new"] == "0571 NEW"


@pytest.mark.django_db
def test_profile_edit_preserves_non_editable_fields(betreuer_user, betreuer_profile):
    """Editing profile should not change name or geburtsdatum."""
    original_name = betreuer_user.get_full_name()
    original_geburtsdatum = betreuer_profile.geburtsdatum

    client = Client()
    client.force_login(betreuer_user)
    client.post('/profil/bearbeiten/', {
        'street': 'Changed Street',
        'house_number': '99',
        'plz': '32425',
        'city': 'Minden',
        'phone': '',
        'kontoinhaber': 'Test',
        'iban': 'DE89370400440532013000',
        'bic': '',
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })

    betreuer_user.refresh_from_db()
    betreuer_profile.refresh_from_db()
    assert betreuer_user.get_full_name() == original_name
    assert betreuer_profile.geburtsdatum == original_geburtsdatum


# ---------------------------------------------------------------------------
# Password change
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_password_change_page_accessible(betreuer_user):
    """Any authenticated user should access the password change page."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/passwort-aendern/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_password_change_unauthenticated_redirect():
    """Unauthenticated user should be redirected to login."""
    client = Client()
    response = client.get('/profil/passwort-aendern/')
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_password_change_valid(betreuer_user):
    """Valid password change should succeed and redirect."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/passwort-aendern/', {
        'old_password': 'testpass123!',
        'new_password1': 'newSecure456!',
        'new_password2': 'newSecure456!',
    })
    assert response.status_code == 302
    assert response.url == '/profil/'

    # Verify new password works
    betreuer_user.refresh_from_db()
    assert betreuer_user.check_password('newSecure456!')


@pytest.mark.django_db
def test_password_change_wrong_old_password(betreuer_user):
    """Wrong old password should be rejected."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/passwort-aendern/', {
        'old_password': 'wrongpassword',
        'new_password1': 'newSecure456!',
        'new_password2': 'newSecure456!',
    })
    assert response.status_code == 200
    assert response.context['form'].errors


@pytest.mark.django_db
def test_password_change_too_short(betreuer_user):
    """Too short password should be rejected by validators."""
    client = Client()
    client.force_login(betreuer_user)
    response = client.post('/profil/passwort-aendern/', {
        'old_password': 'testpass123!',
        'new_password1': 'short',
        'new_password2': 'short',
    })
    assert response.status_code == 200
    assert response.context['form'].errors


@pytest.mark.django_db
def test_password_change_all_roles(admin_user, koordinator_user, betreuer_user):
    """All roles should be able to access the password change page."""
    client = Client()
    for user in [admin_user, koordinator_user, betreuer_user]:
        client.force_login(user)
        response = client.get('/profil/passwort-aendern/')
        assert response.status_code == 200, f"Role {user.username} got {response.status_code}"


# ---------------------------------------------------------------------------
# IBAN Decrypt/Legacy-Value Recovery
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_profile_edit_iban_decrypt_error_recovery(betreuer_user, betreuer_profile):
    """
    Regression-Schutz: Profil-Edit darf NICHT crashen, wenn in der DB ein
    korruptes/legacy-Fernet-verschluesseltes IBAN-Feld steht.

    Szenario: V2 hat IBAN von EncryptedCharField auf CharField migriert.
    Die Data-Migration 0006 dekryptiert legacy Fernet-Tokens. Falls sie
    NICHT lief (FERNET_KEY war leer) oder der Key gedreht wurde, koennen
    Legacy-Ciphertexts wie
        ``gAAAAABh...xyz`` (Fernet-Format) in der DB stehen.

    Erwartung:
    - GET /profil/bearbeiten/ liefert 200 (Form wird gerendert).
    - POST mit neuer, gueltiger IBAN speichert erfolgreich (alter
      korrupter Wert wird ueberschrieben).
    - Keine 500er, kein ValueError, der den Request abreisst.
    """
    # Korrupter/Legacy-Wert wird direkt in die DB geschrieben, damit
    # kein Model-Level-Clean greift. Max. 34 Zeichen (Feld-Length).
    from django.db import connection

    # Fernet-Token-Style (gAAAAABxxx...) abgeschnitten auf max_length=34.
    corrupt_legacy = "gAAAAABh1234KORRUPT_LEGACY_VAL_XX"
    assert len(corrupt_legacy) <= 34
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE contracts_betreuerprofile SET iban = %s WHERE id = %s",
            [corrupt_legacy, betreuer_profile.pk],
        )

    client = Client()
    client.force_login(betreuer_user)

    # 1. GET /profil/bearbeiten/ darf nicht crashen (Form rendern).
    response = client.get('/profil/bearbeiten/')
    assert response.status_code == 200, (
        f"Profil-Edit GET sollte 200 liefern, bekam {response.status_code}. "
        f"Korrupte IBAN-Werte in der DB duerfen keinen Crash ausloesen."
    )

    # 2. POST mit gueltiger neuer IBAN muss erfolgreich speichern und
    #    den korrupten Legacy-Wert ueberschreiben.
    response = client.post('/profil/bearbeiten/', {
        'street': betreuer_profile.street,
        'house_number': betreuer_profile.house_number,
        'plz': betreuer_profile.plz,
        'city': betreuer_profile.city,
        'phone': '',
        'kontoinhaber': betreuer_profile.kontoinhaber,
        'iban': 'DE89370400440532013000',  # frische, gueltige IBAN
        'bic': '',
        'freibetrag_amount_elsewhere': '0',
        'freibetrag_verein_name': '',
    })
    assert response.status_code == 302, (
        "POST mit gueltiger IBAN sollte erfolgreich redirecten (Recovery).  "
        f"Bekam Status {response.status_code}."
    )
    assert response.url == '/profil/'

    # DB-Seite: Neuer Wert ist im Feld (als Klartext).
    betreuer_profile.refresh_from_db()
    assert betreuer_profile.iban == 'DE89370400440532013000'


@pytest.mark.django_db
def test_profile_view_iban_legacy_value_no_crash(betreuer_user, betreuer_profile):
    """
    Profil-Ansicht (/profil/) darf bei einem Legacy-Fernet-Ciphertext
    in iban nicht crashen -- mask_iban() muss defensiv bleiben.
    """
    from django.db import connection

    corrupt_legacy = "gAAAAABLegacyFernetCipherTokXYZ=="  # <= 34 chars
    assert len(corrupt_legacy) <= 34
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE contracts_betreuerprofile SET iban = %s WHERE id = %s",
            [corrupt_legacy, betreuer_profile.pk],
        )

    client = Client()
    client.force_login(betreuer_user)
    response = client.get('/profil/')
    assert response.status_code == 200, (
        "Profilansicht mit korruptem IBAN-Wert muss stabil bleiben."
    )
    # iban_masked sollte im Context existieren (kein Crash bei Rendern).
    assert "iban_masked" in response.context
