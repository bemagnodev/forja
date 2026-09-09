import pytest
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from api.models import User


@pytest.mark.parametrize("invalid_password,reason", [
    ("abc1!", "curta (menos de 8 caracteres)"),
    ("abcdefgh!", "sem dígito"),
    ("12345678!", "sem letra"),
    ("abc12345", "sem caractere especial"),
    ("abc12345 ", "espaço não conta como caractere especial"),
])
def test_password_policy_rejects_invalid_passwords(invalid_password, reason):
    """Testa se a política de senha rejeita senhas inválidas pela razão esperada."""
    with pytest.raises(ValidationError):
        validate_password(invalid_password)


@pytest.mark.parametrize("valid_password", [
    ("abc12345!"),
    ("forja2026#"),
    ("senha123$xyz"),
])
def test_password_policy_accepts_valid_passwords(valid_password):
    """Testa se a política de senha aceita senhas válidas com letra, dígito e especial."""
    validate_password(valid_password)


@pytest.mark.parametrize("accented_password", [
    ("SenhaForte123é!"),
    ("Atenção2026@"),
    ("ÓtimaSenha9#"),
])
def test_password_policy_accepts_accented_letters(accented_password):
    """Testa se a política de senha aceita letras acentuadas (Unicode isalpha)."""
    validate_password(accented_password)


@pytest.mark.parametrize("pure_unicode_password", [
    ("çççççç1!"),
    ("éééééé2@"),
    ("ãããããã3#"),
])
def test_password_policy_counts_accented_characters_as_letters(pure_unicode_password):
    """Testa se a política de senha valida a presença de letras usando puramente caracteres Unicode acentuados (sem letras ASCII)."""
    validate_password(pure_unicode_password)


@pytest.mark.django_db
def test_set_password_endpoint_enforces_password_policy(client):
    """Testa se o endpoint set-password rejeita senhas que descumprem a política do validador."""
    user = User.objects.create(username='user_policy_check', is_active=False)
    user.set_unusable_password()
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    resp = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': 'abc12345'
    }, content_type='application/json')

    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.is_active is False
    assert not user.has_usable_password()
