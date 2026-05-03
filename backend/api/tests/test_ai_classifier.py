import time
import pytest
from unittest.mock import patch, MagicMock, call
from google.api_core.exceptions import ResourceExhausted


# ---------------------------------------------------------------------------
# Testes do MOCK MODE
# ---------------------------------------------------------------------------

def test_mock_mode_returns_fixed_response(monkeypatch):
    """
    Cenário: A variável AI_MOCK_MODE=True está configurada no ambiente.
    Resultado Esperado: classify_problem retorna o JSON fixo de mock sem chamar
    a API do Gemini, e inclui o campo 'reasoning' com 'MOCK MODE ACTIVE'.
    """
    monkeypatch.setenv("AI_MOCK_MODE", "True")
    from api.services.ai_classifier import classify_problem

    result = classify_problem({"title": "Test"})

    assert result["predicted_rating"] == 1200
    assert result["predicted_tags"] == ["implementation"]
    assert result["reasoning"] == "MOCK MODE ACTIVE"


def test_mock_mode_does_not_call_gemini_api(monkeypatch):
    """
    Cenário: AI_MOCK_MODE=True está ativo.
    Resultado Esperado: get_gemini_client NUNCA é instanciado. Isso garante
    que zero cota é consumida durante testes de UI e desenvolvimento local.
    """
    monkeypatch.setenv("AI_MOCK_MODE", "True")

    with patch("api.services.ai_classifier.get_gemini_client") as mock_client:
        from api.services.ai_classifier import classify_problem
        classify_problem({"title": "Test"})
        mock_client.assert_not_called()


def test_mock_mode_simulates_latency(monkeypatch):
    """
    Cenário: AI_MOCK_MODE=True está ativo.
    Resultado Esperado: A função aguarda ~1.5 segundos antes de retornar,
    simulando a latência real da API para testes de UX/loading states.
    """
    monkeypatch.setenv("AI_MOCK_MODE", "True")

    with patch("time.sleep") as mock_sleep:
        from api.services.ai_classifier import classify_problem
        classify_problem({"title": "Test"})
        mock_sleep.assert_called_once_with(1.5)


# ---------------------------------------------------------------------------
# Testes de Seleção de Modelo
# ---------------------------------------------------------------------------

@patch("api.services.ai_classifier.get_gemini_client")
def test_custom_model_name_is_forwarded_to_api(mock_get_client, monkeypatch):
    """
    Cenário: classify_problem é chamado com model_name='gemini-1.5-flash-8b'.
    Resultado Esperado: A chamada à API usa exatamente esse ID de modelo,
    garantindo que o usuário pode selecionar modelos mais econômicos.
    """
    monkeypatch.setenv("AI_MOCK_MODE", "False")

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.parsed = {"predicted_rating": 800, "predicted_tags": ["math"], "reasoning": "Ok"}
    mock_client.models.generate_content.return_value = mock_response

    from api.services.ai_classifier import classify_problem
    classify_problem({"title": "Test"}, model_name="gemini-1.5-flash-8b")

    call_kwargs = mock_client.models.generate_content.call_args
    assert call_kwargs.kwargs["model"] == "gemini-1.5-flash-8b"


@patch("api.services.ai_classifier.get_gemini_client")
def test_default_model_is_read_from_env(mock_get_client, monkeypatch):
    """
    Cenário: GEMINI_DEFAULT_MODEL='gemini-2.0-flash' está no .env e
    classify_problem é chamado SEM o parâmetro model_name.
    Resultado Esperado: A API é chamada com 'gemini-2.0-flash', lendo o
    default do ambiente em vez do hardcoded.
    """
    monkeypatch.setenv("AI_MOCK_MODE", "False")
    monkeypatch.setenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash")

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.parsed = {"predicted_rating": 2000, "predicted_tags": ["dp"], "reasoning": "Hard"}
    mock_client.models.generate_content.return_value = mock_response

    from api.services.ai_classifier import classify_problem
    classify_problem({"title": "Test"})

    call_kwargs = mock_client.models.generate_content.call_args
    assert call_kwargs.kwargs["model"] == "gemini-2.0-flash"


@patch("api.services.ai_classifier.get_gemini_client")
def test_fallback_to_default_model_when_env_not_set(mock_get_client, monkeypatch):
    """
    Cenário: GEMINI_DEFAULT_MODEL NÃO está no .env e model_name não é passado.
    Resultado Esperado: A API é chamada com o default hardcoded 'gemini-1.5-flash',
    nosso 'cavalo de batalha' de 1500 RPD.
    """
    monkeypatch.setenv("AI_MOCK_MODE", "False")
    monkeypatch.delenv("GEMINI_DEFAULT_MODEL", raising=False)

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.parsed = {"predicted_rating": 1200, "predicted_tags": ["greedy"], "reasoning": "Medium"}
    mock_client.models.generate_content.return_value = mock_response

    from api.services.ai_classifier import classify_problem
    classify_problem({"title": "Test"})

    call_kwargs = mock_client.models.generate_content.call_args
    # Deve usar o DEFAULT_MODEL definido em ai_classifier.py quando env não está setado
    from api.services.ai_classifier import DEFAULT_MODEL
    assert call_kwargs.kwargs["model"] == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Testes de Resiliência (Retry)
# ---------------------------------------------------------------------------

@patch("api.services.ai_classifier.get_gemini_client")
@patch("tenacity.nap.time.sleep", return_value=None)
def test_retry_only_on_429_resource_exhausted(mock_sleep, mock_get_client, monkeypatch):
    """
    Cenário: A API retorna 429 ResourceExhausted nas duas primeiras chamadas,
    depois responde com sucesso na terceira.
    Resultado Esperado: Tenacity faz retry e a função completa com sucesso.
    O modelo passado é preservado nas três tentativas.
    """
    monkeypatch.setenv("AI_MOCK_MODE", "False")

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.parsed = {"predicted_rating": 800, "predicted_tags": ["implementation"], "reasoning": "Easy"}

    mock_client.models.generate_content.side_effect = [
        ResourceExhausted("429 Rate limit"),
        ResourceExhausted("429 Rate limit"),
        mock_response,
    ]

    from api.services.ai_classifier import classify_problem
    result = classify_problem({"title": "Test"}, model_name="gemini-2.5-flash")

    assert mock_client.models.generate_content.call_count == 3
    assert result["predicted_rating"] == 800
