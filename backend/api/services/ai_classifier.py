import os
import time
import json
from google import genai
from google.genai import types
from google.genai import errors
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# ---------------------------------------------------------------------------
# Tabela de modelos CONFIRMADOS como disponíveis nesta chave de API.
# Os IDs gemini-1.5-* não estão disponíveis via v1beta (novo SDK google-genai).
SUPPORTED_MODELS = {
    "gemini-3.1-flash-lite-preview": {"daily_limit": 500,    "label": "Gemini 3 Lite"},
    "gemini-2.5-flash":              {"daily_limit": 20,     "label": "Gemini 2.5 Flash"},
    "gemini-3-flash-preview":        {"daily_limit": 20,     "label": "Gemini 3.0 Flash"},
}

# Padrão: lê do .env, fallback para o gemini-2.5-flash (confirmado com cota nesta chave)
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"

# Contador em memória de requisições por modelo nesta sessão
_request_counter: dict[str, int] = {m: 0 for m in SUPPORTED_MODELS}

# Schema estrito da resposta — o SDK serializa os campos separadamente,
# eliminando problemas de escaping de LaTeX em strings JSON livres.
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["predicted_rating", "predicted_tags", "reasoning"],
    properties={
        "predicted_rating": types.Schema(
            type=types.Type.INTEGER,
            description="Dificuldade estimada do problema (múltiplo de 100, entre 800 e 3500).",
        ),
        "predicted_tags": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
            description="Lista de 1 a 3 tags oficiais do Codeforces.",
        ),
        "reasoning": types.Schema(
            type=types.Type.STRING,
            description="Explicação do raciocínio utilizado para a classificação.",
        ),
    },
)

# Lista oficial de tags do CF para guiar o modelo e evitar alucinações
OFFICIAL_TAGS = (
    "2-sat, binary search, bitmasks, brute force, chinese remainder theorem, "
    "combinatorics, constructive algorithms, data structures, dfs and similar, "
    "divide and conquer, dp, dsu, expression parsing, fft, flows, games, "
    "geometry, graph matchings, graphs, greedy, hashing, implementation, "
    "interactive, math, matrices, meet-in-the-middle, number theory, "
    "probabilities, schedules, shortest paths, sortings, string suffix structures, "
    "strings, ternary search, trees, two pointers"
)


def get_gemini_client():
    """Cria o cliente de forma lazy para não bloquear import em testes sem chave."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)


def classify_problem(problem_data: dict, model_name: str = None) -> dict:
    """
    Ponto de entrada principal. Orquestra o mock mode e a seleção de modelo
    antes de delegar a chamada real à API.

    Args:
        problem_data: Dicionário com metadados do problema (do Scraper).
        model_name: ID do modelo Gemini. Se None, lê GEMINI_DEFAULT_MODEL do .env
                    ou usa 'gemini-1.5-flash' como fallback final.
    """
    # 1. Mock Mode — intercepta ANTES de qualquer chamada à API
    if os.environ.get("AI_MOCK_MODE", "").lower() == "true":
        time.sleep(1.5)  # simula a latência real de rede para testes de UX
        return {
            "predicted_rating": 1200,
            "predicted_tags": ["implementation"],
            "reasoning": "MOCK MODE ACTIVE",
        }

    # 2. Resolve o modelo a usar: parâmetro > .env > hardcoded default
    resolved_model = model_name or os.environ.get("GEMINI_DEFAULT_MODEL", DEFAULT_MODEL)

    # 3. Delega para a função com retry (decorada com Tenacity)
    return _call_gemini_with_retry(problem_data, resolved_model)

def is_retryable_error(exc):
    """Retorna True se o erro for recuperável (ex: rate limit 429)."""
    if isinstance(exc, errors.APIError):
        # APIError contém informações no próprio objeto em vez de response HTTP
        return "429" in str(exc) or "quota" in str(exc).lower()
    return False

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    # Retry apenas para 429 (rate limit). 503 é tratado como erro não-recuperável
    # para evitar esperas longas em falhas estruturais da API.
    retry=retry_if_exception_type(errors.APIError),
)
def _call_gemini_with_retry(problem_data: dict, model_name: str) -> dict:
    """
    Chamada real à API do Gemini com retry automático em caso de 429.
    Separada de classify_problem para que o @retry não interfira com o mock mode.
    """
    prompt = f"""Você é um Grandmaster de Programação Competitiva com profundo conhecimento do Codeforces.
Analise o enunciado do problema abaixo e:
1. Estime o `predicted_rating` (número inteiro, múltiplo de 100, entre 800 e 3500).
2. Sugira de 1 a 3 `predicted_tags` EXCLUSIVAMENTE desta lista oficial: [{OFFICIAL_TAGS}].
3. Escreva um `reasoning` detalhado explicando a abordagem e o porquê do rating.

Dica: se `total_solved` estiver disponível, use-o como sinal forte de dificuldade
(muitos AC → problema mais fácil; poucos AC → mais difícil).

Dados do problema:
{json.dumps(problem_data, ensure_ascii=False, indent=2)}
"""

    client = get_gemini_client()

    # thinking_budget é suportado apenas nos modelos gemini-2.5+
    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
    )
    if "2.5" in model_name:
        gen_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=gen_config,
    )

    # Atualiza contador de sessão e loga o consumo
    _log_usage(model_name)

    try:
        return response.parsed
    except Exception:
        # Fallback: tenta parsear o texto bruto se response.parsed falhar
        try:
            return json.loads(response.text)
        except Exception as e:
            return {
                "predicted_rating": None,
                "predicted_tags": [],
                "reasoning": f"Parse error: {e}. Raw: {getattr(response, 'text', 'N/A')}",
            }


def _log_usage(model_name: str) -> None:
    """Atualiza e imprime o log de consumo de cota estimado da sessão."""
    if model_name in _request_counter:
        _request_counter[model_name] += 1
        count = _request_counter[model_name]
        limit = SUPPORTED_MODELS.get(model_name, {}).get("daily_limit", "N/A")
        label = SUPPORTED_MODELS.get(model_name, {}).get("label", model_name)
        print(f"\n[Forja AI] Requisição enviada ao modelo [{label} / {model_name}]. "
              f"Cota diária estimada: {count}/{limit} RPD")

