"""Thinking experiments must persist exactly the configuration sent to Gemini."""
import json
from types import SimpleNamespace

import pytest
from django.core.management import call_command, CommandError


@pytest.mark.parametrize("level", ["minimal", "high"])
@pytest.mark.parametrize("timeout", [None, 90])
def test_command_saves_and_sends_thinking_and_rejects_changed_resume(level, timeout, reviewed_manifest, tmp_path, monkeypatch):
    from api.ai_lab.providers import gemini
    from api.ai_lab.runner import save_json
    from api.management.commands import run_ai_benchmark as command

    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", reviewed_manifest())
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key")
    monkeypatch.setenv("AI_LAB_FREE_TIER_CONFIRMED", "true")
    sent = []
    timeouts = []

    def generate_content(**kwargs):
        sent.append(kwargs["config"])
        return SimpleNamespace(parsed={"rating": 1200, "tags": ["math"], "justification": "synthetic"},
                               usage_metadata=None, candidates=[])

    def client(**kwargs):
        timeouts.append(kwargs["http_options"].timeout)
        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(gemini.genai, "Client", client)
    options = dict(classifier="gemini", model="gemini-3.5-flash-lite", allow_model="gemini-3.5-flash-lite",
                   run_id="thinking", max_requests=1, thinking_level=level)
    if timeout is not None:
        options["timeout_seconds"] = timeout
    call_command("run_ai_benchmark", **options)
    path = tmp_path / "runs/thinking/run.json"
    before = path.read_bytes()
    run = json.loads(before)
    assert run["configuration"]["generation"]["thinking_level"] == level
    assert sent[0].thinking_config.thinking_level.value.lower() == level
    assert run["configuration"]["timeout_seconds"] == (timeout or 30)
    assert timeouts == [(timeout or 30) * 1000]
    call_command("run_ai_benchmark", **options)
    assert len(sent) == 1
    if timeout is not None:
        with pytest.raises(CommandError, match="configuration"):
            call_command("run_ai_benchmark", **{**options, "timeout_seconds": 60})
        assert path.read_bytes() == before
    for changed in [None, "high" if level == "minimal" else "minimal"]:
        with pytest.raises(CommandError, match="configuration"):
            call_command("run_ai_benchmark", **{**options, "thinking_level": changed})
        assert path.read_bytes() == before
    assert len(sent) == 1


@pytest.mark.parametrize("classifier,model,level", [
    ("baseline", None, "high"), ("groq", "openai/gpt-oss-120b", "high"),
    ("gemini", "gemini-3.8-flash", "high"), ("gemini", "gemini-3.5-flash-lite", "invalid"),
])
def test_invalid_thinking_rejected_before_resolving_generator(classifier, model, level, tmp_path, monkeypatch):
    from api.management.commands import run_ai_benchmark as command
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setattr(command, "get_generator", lambda *a, **kw: pytest.fail("must not call"))
    with pytest.raises(CommandError, match="[Tt]hinking|thinking_level|invalid choice"):
        call_command("run_ai_benchmark", classifier=classifier, model=model, thinking_level=level)
    assert not (tmp_path / "runs").exists()


def test_adapter_records_thinking_tokens_and_finish_reason():
    from api.ai_lab.providers.gemini import generate
    from google.genai import types
    response = SimpleNamespace(
        parsed={"rating": 1200, "tags": ["math"]},
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=10, candidates_token_count=5, thoughts_token_count=30, total_token_count=45),
        candidates=[types.Candidate(finish_reason=types.FinishReason.STOP)])
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: response))
    result = generate({}, "synthetic", "gemini-3.5-flash-lite", client=client, thinking_level="high")
    assert result["_usage"]["thinking_tokens"] == 30
    assert result["_finish_reason"] == "STOP"


def test_default_generator_does_not_enable_explicit_thinking():
    from api.ai_lab.classification import get_generator
    from api.ai_lab.providers.gemini import generate
    assert get_generator("gemini", "gemini-3.5-flash-lite") is generate


def test_invalid_adapter_level_is_rejected_before_creating_client(monkeypatch):
    from api.ai_lab.providers import gemini
    monkeypatch.setattr(gemini.genai, "Client", lambda **kw: pytest.fail("must not create client"))
    with pytest.raises(ValueError, match="[Tt]hinking"):
        gemini.generate({}, "synthetic", "gemini-3.5-flash-lite", thinking_level="invalid")


@pytest.mark.parametrize("timeout", [0, -1, 121, float("nan"), float("inf")])
def test_invalid_timeout_rejected_before_inference(timeout, tmp_path, monkeypatch):
    from api.management.commands import run_ai_benchmark as command
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setattr(command, "get_generator", lambda *a, **kw: pytest.fail("must not call"))
    with pytest.raises(CommandError, match="[Tt]imeout"):
        call_command("run_ai_benchmark", classifier="gemini", model="gemini-3.5-flash-lite", timeout_seconds=timeout)
