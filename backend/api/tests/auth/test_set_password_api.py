import re
import urllib.parse
from io import StringIO
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from api.models import User


@pytest.mark.django_db
def test_set_password_activates_invited_user(client):
    """
    Cenário:
    Definição de senha via POST /api/auth/set-password para um convidado inativo.

    Resultado esperado:
    - O usuário torna-se is_active=True e a nova senha é gravada.
    - A reutilização do mesmo token na sequência retorna 400.
    """
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

    resp_reuse = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': 'OutraSenhaValida123!'
    }, content_type='application/json')
    assert resp_reuse.status_code == 400


@pytest.mark.django_db
def test_set_password_invalid_token_does_not_activate_user(client):
    """
    Cenário:
    Requisição ao endpoint com um token inválido.

    Resultado esperado:
    - Retorna status 400.
    - O status is_active permanece False e nenhuma senha válida é registrada.
    """
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
    """
    Cenário:
    Requisição com um UID malformado/inválido.

    Resultado esperado:
    - Retorna status 400.
    """
    resp = client.post('/api/auth/set-password', data={
        'uid': 'invalid-uid-xxx',
        'token': 'some-token',
        'password': 'NovaSenhaValida123!'
    }, content_type='application/json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_set_password_reset_flow_preserves_old_password_until_used(client):
    """
    Cenário:
    Geração de link de redefinição para conta ativa.

    Resultado esperado:
    - A senha antiga continua funcional até o envio do POST /api/auth/set-password.
    - Após o sucesso, a nova senha passa a valer e a antiga é invalidada.
    """
    user = User.objects.create_user(
        username='usuario_reset_flow',
        password='SenhaAntiga123!'
    )
    user.is_active = True
    user.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

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


@pytest.mark.django_db
def test_integration_invite_user_real_link_consumed_successfully(client):
    """
    Cenário:
    Fluxo de integração completo do convite — execução do comando invite_user, extração da URL do stdout e consumo do endpoint.

    Resultado esperado:
    - Extração bem sucedida dos parâmetros uid e token da URL impressa.
    - Ativação da conta do usuário e gravação da senha digitada.
    """
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
    """
    Cenário:
    Fluxo de integração completo do reset — execução do comando reset_user_password, extração da URL e consumo da redefinição.

    Resultado esperado:
    - Senha antiga mantida antes do consumo do link.
    - Nova senha gravada com sucesso e antiga desativada.
    """
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
    """
    Cenário:
    Tentativa de consumo de um token gerado há mais de 3 dias (simulado via patch de _now).

    Resultado esperado:
    - O endpoint rejeita com status 400.
    - O usuário permanece inativo e sem senha.
    """
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
    """
    Cenário:
    Execução de reset_user_password para uma conta inativa (convite pendente).

    Resultado esperado:
    - O comando regenera o link sem alterar a inatividade do usuário.
    - Apenas ao consumir o link a conta torna-se is_active=True.
    """
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
