"""Provider boundary tests use in-process HTTP, never real keys or network."""
import json

import httpx
import pytest

MODELS = ("openai/gpt-oss-120b", "qwen/qwen3.8-27b")


@pytest.mark.parametrize("model", MODELS)
def test_groq_sends_fixed_input_and_schema_without_tools(model, monkeypatch):
    from api.ai_lab.providers.groq import generate

    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({
                "rating": 1200, "tags": ["math"], "justification": "Synthetic approach"})}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40},
        })

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = generate({"description": "Synthetic statement"}, "fixed v1", model, client=client)

    assert len(requests) == 1
    assert str(requests[0].url) == "https://api.groq.com/openai/v1/chat/completions"
    body = json.loads(requests[0].content)
    assert body["model"] == model
    assert body["messages"] == [
        {"role": "system", "content": "fixed v1"},
        {"role": "user", "content": json.dumps({"description": "Synthetic statement"}, ensure_ascii=False)},
    ]
    assert "tools" not in body and "search_settings" not in body
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] == 4096
    if model == "qwen/qwen3.8-27b":
        assert body.get("reasoning_format") == "hidden"
    else:
        assert "reasoning_format" not in body
    assert result["rating"] == 1200
    assert result["_usage"] == {"input_tokens": 30, "output_tokens": 10, "total_tokens": 40}


@pytest.mark.parametrize("code,category", [(401, "authentication"), (403, "authentication"),
                                         (429, "rate_limit"), (503, "server_error"), (400, "provider_error")])
def test_groq_errors_are_sanitized_and_never_retried(code, category, monkeypatch):
    from api.ai_lab.providers.groq import generate
    from api.ai_lab.contracts import ProviderFailure

    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(code, headers={"Retry-After": "90"}, text="private error body")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ProviderFailure) as error:
            generate({}, "prompt", MODELS[0], client=client)
    assert error.value.category == category
    assert error.value.retry_after == 90
    assert error.value.responded is False
    assert "private" not in str(error.value)
    assert len(requests) == 1


@pytest.mark.parametrize("response", [
    {"choices": []},
    {"choices": [{"finish_reason": "stop", "message": {"content": "not JSON"}}]},
    {"choices": [{"finish_reason": "length", "message": {"content": '{"rating":1200}'}}]},
    {"choices": [{"finish_reason": "stop", "message": {"content": "[]"}}]},
])
def test_groq_rejects_malformed_or_truncated_response(response, monkeypatch):
    from api.ai_lab.providers.groq import generate
    from api.ai_lab.contracts import ProviderFailure

    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response))) as client:
        with pytest.raises(ProviderFailure, match="parsing") as error:
            generate({}, "prompt", MODELS[1], client=client)
    assert error.value.responded is True


def test_groq_timeout_has_no_retry(monkeypatch):
    from api.ai_lab.providers.groq import generate
    from api.ai_lab.contracts import ProviderFailure

    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    requests = []

    def timeout(request):
        requests.append(request)
        raise httpx.ReadTimeout("private detail", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ProviderFailure, match="timeout"):
            generate({}, "prompt", MODELS[0], client=client)
    assert len(requests) == 1


def test_groq_requires_key_and_reviewed_model_before_http(monkeypatch):
    from api.ai_lab.providers.groq import generate
    from api.ai_lab.contracts import ProviderFailure

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ProviderFailure, match="authentication"):
        generate({}, "prompt", MODELS[0])
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    with pytest.raises(ValueError, match="model"):
        generate({}, "prompt", "unapproved-model")
