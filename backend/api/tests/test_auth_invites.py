import pytest
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from api.models import User

@pytest.mark.django_db
def test_invite_user_creates_pending_user():
    """Testa se invite_user cria usuário novo com is_active=False e senha inutilizável."""
    out = StringIO()
    call_command(
        'invite_user',
        'novo_membro',
        cf_handle='novo_cf',
        atcoder_handle='novo_atcoder',
        email='novo@example.com',
        stdout=out
    )

    user = User.objects.get(username='novo_membro')
    assert user.cf_handle == 'novo_cf'
    assert user.atcoder_handle == 'novo_atcoder'
    assert user.email == 'novo@example.com'
    assert user.is_active is False
    assert not user.has_usable_password()

    output = out.getvalue()
    assert '/set-password' in output
    assert 'uid=' in output
    assert 'token=' in output

@pytest.mark.django_db
def test_invite_user_fails_if_user_already_exists():
    """Testa se invite_user falha com CommandError e orienta reset_user_password para usuário existente."""
    user = User.objects.create_user(
        username='membro_existente',
        email='original@example.com',
        password='Password123!',
        cf_handle='original_cf',
        atcoder_handle='original_atcoder'
    )
    user.is_active = True
    user.save()

    out = StringIO()
    with pytest.raises(CommandError) as exc_info:
        call_command(
            'invite_user',
            'membro_existente',
            cf_handle='novo_cf',
            atcoder_handle='novo_atcoder',
            email='novo@example.com',
            stdout=out
        )

    assert "reset_user_password" in str(exc_info.value)

    # Garante que nada foi alterado no usuário existente
    user.refresh_from_db()
    assert user.email == 'original@example.com'
    assert user.cf_handle == 'original_cf'
    assert user.atcoder_handle == 'original_atcoder'
    assert user.is_active is True
    assert user.check_password('Password123!')

@pytest.mark.django_db
def test_reset_user_password_fails_for_nonexistent_user():
    """Testa se reset_user_password falha com CommandError para usuário inexistente."""
    out = StringIO()
    with pytest.raises(CommandError) as exc_info:
        call_command('reset_user_password', 'usuario_inexistente', stdout=out)
    assert "não foi encontrado" in str(exc_info.value).lower() or "não existe" in str(exc_info.value).lower()

@pytest.mark.django_db
def test_reset_user_password_success_and_does_not_modify_user_data(settings):
    """Testa se reset_user_password gera link sem alterar dados, status ou senha atual."""
    settings.FRONTEND_URL = 'https://forja-test.vercel.app'
    user = User.objects.create_user(
        username='membro_reset',
        email='membro@example.com',
        password='SenhaAtual123!',
        cf_handle='membro_cf',
        atcoder_handle='membro_atcoder'
    )
    user.is_active = True
    user.save()

    out = StringIO()
    call_command('reset_user_password', 'membro_reset', stdout=out)

    output = out.getvalue()
    assert 'https://forja-test.vercel.app/set-password' in output
    assert 'uid=' in output
    assert 'token=' in output

    user.refresh_from_db()
    assert user.email == 'membro@example.com'
    assert user.cf_handle == 'membro_cf'
    assert user.atcoder_handle == 'membro_atcoder'
    assert user.is_active is True
    assert user.check_password('SenhaAtual123!')

@pytest.mark.django_db
def test_reset_user_password_custom_base_url():
    """Testa se reset_user_password respeita o parâmetro --base_url."""
    user = User.objects.create_user(
        username='membro_local',
        password='SenhaAtual123!'
    )
    out = StringIO()
    call_command('reset_user_password', 'membro_local', base_url='http://localhost:5173/', stdout=out)

    output = out.getvalue()
    assert 'http://localhost:5173/set-password' in output
    assert 'http://localhost:5173//set-password' not in output

@pytest.mark.django_db
def test_set_password_activates_invited_user(client):
    """Testa se aceitação de convite define senha, torna is_active=True e invalida token."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    user = User.objects.create(
        username='convidado_inativo',
        is_active=False
    )
    user.set_unusable_password()
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    resp = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': 'NovaSenhaValida123!'
    }, content_type='application/json')

    assert resp.status_code == 200
    assert resp.json()['success'] is True

    user.refresh_from_db()
    assert user.is_active is True
    assert user.check_password('NovaSenhaValida123!')

    # Reutilização do token deve falhar
    resp_reuse = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': 'OutraSenhaValida123!'
    }, content_type='application/json')
    assert resp_reuse.status_code == 400

@pytest.mark.django_db
def test_set_password_invalid_token_does_not_activate_user(client):
    """Testa se token inválido rejeita sem alterar is_active nem definir senha."""
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    user = User.objects.create(
        username='convidado_preservado',
        is_active=False
    )
    user.set_unusable_password()
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))

    resp = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': 'token-invalido-123',
        'password': 'NovaSenhaValida123!'
    }, content_type='application/json')

    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.is_active is False
    assert not user.has_usable_password()

@pytest.mark.django_db
def test_set_password_invalid_uid_returns_bad_request(client):
    """Testa se UID inválido retorna 400."""
    resp = client.post('/api/auth/set-password', data={
        'uid': 'invalid-uid-xxx',
        'token': 'some-token',
        'password': 'NovaSenhaValida123!'
    }, content_type='application/json')
    assert resp.status_code == 400

@pytest.mark.django_db
def test_set_password_reset_flow_preserves_old_password_until_used(client):
    """Testa se fluxo de reset mantém senha antiga funcional até o uso do link."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    user = User.objects.create_user(
        username='usuario_reset_flow',
        password='SenhaAntiga123!'
    )
    user.is_active = True
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Senha antiga funciona antes do link ser usado
    user.refresh_from_db()
    assert user.check_password('SenhaAntiga123!')

    resp = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': 'NovaSenha123!'
    }, content_type='application/json')
    assert resp.status_code == 200

    user.refresh_from_db()
    assert user.is_active is True
    assert user.check_password('NovaSenha123!')
    assert not user.check_password('SenhaAntiga123!')

@pytest.mark.parametrize("invalid_password,reason", [
    ("abc1!", "curta (menos de 8 caracteres)"),
    ("abcdefgh!", "sem dígito"),
    ("12345678!", "sem letra"),
    ("abc12345", "sem caractere especial"),
    ("abc12345 ", "espaço não conta como caractere especial"),
])
def test_password_policy_rejects_invalid_passwords(invalid_password, reason):
    """Testa se a política de senha rejeita senhas inválidas pela razão esperada."""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        validate_password(invalid_password)

@pytest.mark.parametrize("valid_password", [
    ("abc12345!"),
    ("forja2026#"),
    ("senha123$xyz"),
])
def test_password_policy_accepts_valid_passwords(valid_password):
    """Testa se a política de senha aceita senhas válidas com letra, dígito e especial."""
    from django.contrib.auth.password_validation import validate_password

    # Não deve levantar ValidationError
    validate_password(valid_password)

@pytest.mark.django_db
def test_set_password_endpoint_enforces_password_policy(client):
    """Testa se o endpoint set-password rejeita senhas que descumprem a política do validador."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    user = User.objects.create(username='user_policy_check', is_active=False)
    user.set_unusable_password()
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Senha com 8 caracteres, letra e número, mas sem especial: "abc12345"
    resp = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': 'abc12345'
    }, content_type='application/json')

    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.is_active is False
    assert not user.has_usable_password()

import re
import urllib.parse
from unittest.mock import patch
from datetime import datetime, timedelta

@pytest.mark.parametrize("accented_password", [
    ("SenhaForte123é!"),
    ("Atenção2026@"),
    ("ÓtimaSenha9#"),
])
def test_password_policy_accepts_accented_letters(accented_password):
    """Testa se a política de senha aceita letras acentuadas (Unicode isalpha)."""
    from django.contrib.auth.password_validation import validate_password
    validate_password(accented_password)

@pytest.mark.django_db
def test_integration_invite_user_real_link_consumed_successfully(client):
    """Testa o fluxo ponta a ponta do link real impresso por invite_user."""
    out = StringIO()
    call_command('invite_user', 'aluno_integracao', email='aluno@forja.test', stdout=out)

    output = out.getvalue()
    match = re.search(r'https?://[^\s]+', output)
    assert match is not None, "URL não encontrada na saída do comando"

    real_url = match.group(0)
    parsed = urllib.parse.urlparse(real_url)
    qs = urllib.parse.parse_qs(parsed.query)

    assert 'uid' in qs and 'token' in qs
    extracted_uid = qs['uid'][0]
    extracted_token = qs['token'][0]

    user = User.objects.get(username='aluno_integracao')
    assert user.is_active is False
    assert not user.has_usable_password()

    resp = client.post('/api/auth/set-password', data={
        'uid': extracted_uid,
        'token': extracted_token,
        'password': 'SenhaIntegracao123!'
    }, content_type='application/json')

    assert resp.status_code == 200
    assert resp.json()['success'] is True

    user.refresh_from_db()
    assert user.is_active is True
    assert user.check_password('SenhaIntegracao123!')

@pytest.mark.django_db
def test_integration_reset_user_password_real_link_consumed_successfully(client):
    """Testa o fluxo ponta a ponta do link real impresso por reset_user_password para usuário ativo."""
    user = User.objects.create_user(
        username='membro_ativo_reset',
        password='SenhaAntiga123!'
    )
    user.is_active = True
    user.save()

    out = StringIO()
    call_command('reset_user_password', 'membro_ativo_reset', stdout=out)

    output = out.getvalue()
    match = re.search(r'https?://[^\s]+', output)
    assert match is not None

    real_url = match.group(0)
    parsed = urllib.parse.urlparse(real_url)
    qs = urllib.parse.parse_qs(parsed.query)

    extracted_uid = qs['uid'][0]
    extracted_token = qs['token'][0]

    # Senha antiga continua válida antes do uso do link
    user.refresh_from_db()
    assert user.check_password('SenhaAntiga123!')

    resp = client.post('/api/auth/set-password', data={
        'uid': extracted_uid,
        'token': extracted_token,
        'password': 'NovaSenhaReset123!'
    }, content_type='application/json')

    assert resp.status_code == 200
    assert resp.json()['success'] is True

    user.refresh_from_db()
    assert user.is_active is True
    assert user.check_password('NovaSenhaReset123!')
    assert not user.check_password('SenhaAntiga123!')

@pytest.mark.django_db
def test_token_expiration_after_three_days(client):
    """Testa que após 3 dias o token expira, endpoint retorna 400 e dados do usuário não mudam."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    user = User.objects.create(username='convidado_expira', is_active=False)
    user.set_unusable_password()
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    future_time = datetime.now() + timedelta(days=3, seconds=10)
    with patch.object(default_token_generator, '_now', return_value=future_time):
        resp = client.post('/api/auth/set-password', data={
            'uid': uid,
            'token': token,
            'password': 'NovaSenhaValida123!'
        }, content_type='application/json')

    assert resp.status_code == 400
    user.refresh_from_db()
    assert user.is_active is False
    assert not user.has_usable_password()

@pytest.mark.django_db
def test_reset_user_password_on_inactive_user_regenerates_link_without_activating(client):
    """Testa que reset_user_password em usuário inativo não ativa a conta; a ativação ocorre no consumo."""
    user = User.objects.create(username='convidado_reenvio', is_active=False)
    user.set_unusable_password()
    user.save()

    out = StringIO()
    call_command('reset_user_password', 'convidado_reenvio', stdout=out)

    output = out.getvalue()
    assert 'permanece inativa até que este link seja utilizado' in output

    user.refresh_from_db()
    assert user.is_active is False
    assert not user.has_usable_password()

    # Consumir o link regenerado ativa o usuário
    match = re.search(r'https?://[^\s]+', output)
    assert match is not None
    real_url = match.group(0)
    parsed = urllib.parse.urlparse(real_url)
    qs = urllib.parse.parse_qs(parsed.query)

    resp = client.post('/api/auth/set-password', data={
        'uid': qs['uid'][0],
        'token': qs['token'][0],
        'password': 'SenhaReenvio123!'
    }, content_type='application/json')

    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True
    assert user.check_password('SenhaReenvio123!')





