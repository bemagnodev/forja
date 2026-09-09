from io import StringIO
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from api.models import User


@pytest.mark.django_db
def test_invite_user_creates_pending_user():
    """
    Cenário:
    Execução do comando invite_user para um novo usuário.

    Resultado esperado:
    - Usuário criado com is_active=False e sem senha utilizável.
    - Saída no stdout contendo o link com uid e token.
    """
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
    """
    Cenário:
    Tentativa de convidar um usuário cujo username já existe no banco.

    Resultado esperado:
    - O comando levanta CommandError instruindo a usar reset_user_password.
    - Os dados do usuário existente permanecem intactos.
    """
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

    user.refresh_from_db()
    assert user.email == 'original@example.com'
    assert user.cf_handle == 'original_cf'
    assert user.atcoder_handle == 'original_atcoder'
    assert user.is_active is True
    assert user.check_password('Password123!')


@pytest.mark.django_db
def test_invite_and_set_password(client):
    """
    Cenário:
    Geração do token pelo comando invite_user e posterior ativação/definição de senha via API.

    Resultado esperado:
    - Validação falha para senha inválida/curta.
    - Sucesso ao fornecer senha válida, gravando o hash no usuário.
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    out = StringIO()
    call_command('invite_user', 'novo_colega', cf_handle='colega_cf', stdout=out)
    
    user = User.objects.get(username='novo_colega')
    assert user.cf_handle == 'colega_cf'
    assert not user.has_usable_password()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    resp_bad = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': '123'
    }, content_type='application/json')
    assert resp_bad.status_code == 400

    resp_ok = client.post('/api/auth/set-password', data={
        'uid': uid,
        'token': token,
        'password': 'SenhaForte123!'
    }, content_type='application/json')
    assert resp_ok.status_code == 200
    assert resp_ok.json()['success'] is True

    user.refresh_from_db()
    assert user.check_password('SenhaForte123!')
