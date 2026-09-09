from io import StringIO
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from api.models import User


@pytest.mark.django_db
def test_reset_user_password_fails_for_nonexistent_user():
    """
    Cenário:
    Execução do comando reset_user_password para um usuário inexistente.

    Resultado esperado:
    - O comando levanta CommandError indicando que o usuário não foi encontrado.
    """
    out = StringIO()
    with pytest.raises(CommandError) as exc_info:
        call_command('reset_user_password', 'usuario_inexistente', stdout=out)
    assert "não foi encontrado" in str(exc_info.value).lower() or "não existe" in str(exc_info.value).lower()


@pytest.mark.django_db
def test_reset_user_password_success_and_does_not_modify_user_data(settings):
    """
    Cenário:
    Geração de link de redefinição de senha para um usuário ativo existente.

    Resultado esperado:
    - Impressão do link contendo a URL base configurada em FRONTEND_URL.
    - Preservação dos dados, status (is_active) e senha atual do usuário.
    """
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
    """
    Cenário:
    Uso do argumento --base_url ao executar reset_user_password.

    Resultado esperado:
    - O link gerado utiliza a base_url informada sem barras duplicadas.
    """
    user = User.objects.create_user(
        username='membro_local',
        password='SenhaAtual123!'
    )
    out = StringIO()
    call_command('reset_user_password', 'membro_local', base_url='http://localhost:5173/', stdout=out)

    output = out.getvalue()
    assert 'http://localhost:5173/set-password' in output
    assert 'http://localhost:5173//set-password' not in output
