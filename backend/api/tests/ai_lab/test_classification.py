import pytest


@pytest.mark.parametrize("managed", [True, False])
@pytest.mark.parametrize("mode", ["raise", "unserializable"])
def test_unexpected_error_is_safe_preserves_attempt_and_cannot_repeat_uncertain_item(managed, mode, reviewed_manifest, tmp_path):
    import json
    from datetime import datetime
    from api.ai_lab.runner import run_local
    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": "classification_v1", "max_attempts": 3, "request_interval": 0, "max_wait": 60}
    if not managed:
        config.pop("execution_policy")
    calls = []

    def generate(prepared, *args):
        calls.append(prepared)
        if len(calls) == 2:
            if mode == "unserializable":
                return {"rating": 1200, "tags": ["math"], "private": "PRIVATE_RESPONSE_AND_API_SECRET", "bad": {object()}}
            raise RuntimeError("PRIVATE_RESPONSE_AND_API_SECRET")
        return {"rating": 1200, "tags": ["math"]}

    with pytest.raises(RuntimeError, match="Unexpected benchmark error") as failure:
        run_local(manifest, config, path, generate, max_requests=3)
    assert "PRIVATE_RESPONSE_AND_API_SECRET" not in str(failure.value)
    saved = json.loads(path.read_text())
    assert saved["stop_reason"] == "unexpected_error"
    assert saved["unexpected_error"]["type"] == ("RuntimeError" if mode == "raise" else "TypeError")
    assert datetime.fromisoformat(saved["unexpected_error"]["at"]).tzinfo is not None
    assert set(saved["unexpected_error"]) == {"type", "at"}
    assert "PRIVATE_RESPONSE_AND_API_SECRET" not in path.read_text()
    assert saved["request_count"] == 2 and saved["authorized_request_limit"] == 3
    first, uncertain, third = [item["key"] for item in manifest["items"][:3]]
    assert saved["predictions"][first]["rating_status"] == "valid"
    assert saved["predictions"][uncertain]["error"] == "interrupted"
    assert saved["attempt_history"][uncertain][0]["state"] == "started"
    assert not path.with_suffix(".lock").exists()
    resumed = run_local(manifest, config, path, generate, max_requests=3)
    assert len(calls) == 3 and resumed["request_count"] == 3
    assert resumed["predictions"][first] == saved["predictions"][first]
    assert resumed["predictions"][uncertain] == saved["predictions"][uncertain]
    assert resumed["attempt_history"][uncertain] == saved["attempt_history"][uncertain]
    assert resumed["predictions"][third]["rating_status"] == "valid"


def test_rubric_prompt_loads_with_same_output_contract():
    from api.ai_lab.classification import load_prompt
    prompt = load_prompt("classification_v2")
    assert "Descoberta da ideia" in prompt and "solução viável mais simples" in prompt
    assert "{taxonomy}" not in prompt and "binary search" in prompt
    assert all(field in prompt for field in ("rating:", "tags:", "justification:"))
    assert "soma ou média fixa" in prompt


def test_few_shot_draft_cannot_run_with_missing_examples():
    from api.ai_lab.classification import load_prompt
    with pytest.raises(ValueError, match="examples"):
        load_prompt("classification_v3")


def test_named_prompt_rejects_paths_and_loads_version():
    from api.ai_lab.classification import load_prompt
    assert load_prompt("classification_v1") == load_prompt()
    with pytest.raises(ValueError):
        load_prompt("../classification_v1")


def test_managed_prompt_and_policy_changes_cannot_overwrite_run(reviewed_manifest, tmp_path, monkeypatch):
    import json
    from api.ai_lab import runner
    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": "classification_v1", "max_attempts": 3, "request_interval": 0, "max_wait": 60}
    runner.run_local(manifest, config, path, lambda *a: {"rating": 1200, "tags": ["math"]}, max_requests=1)
    original = json.loads(path.read_text())
    monkeypatch.setattr(runner, "load_prompt", lambda version: "different prompt")
    with pytest.raises(ValueError, match="configuration"):
        runner.run_local(manifest, config, path, lambda *a: pytest.fail("must not call"), max_requests=60)
    assert json.loads(path.read_text()) == original


def test_managed_interruption_preserves_budget_and_does_not_repeat_unknown(reviewed_manifest, tmp_path):
    import json
    from api.ai_lab.runner import run_local
    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": "classification_v1", "max_attempts": 3, "request_interval": 0, "max_wait": 60}
    def interrupt(*args):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run_local(manifest, config, path, interrupt, max_requests=2)
    assert json.loads(path.read_text())["request_count"] == 1
    resumed = run_local(manifest, config, path, lambda *a: {"rating": 1200, "tags": ["math"]}, max_requests=2)
    assert len(resumed["predictions"]) == 2
    assert next(iter(resumed["predictions"].values()))["error"] == "interrupted"


def test_managed_run_recovers_continues_and_preserves_total_budget(reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local, summarize_run
    from api.ai_lab.contracts import ProviderFailure
    calls, waits = [], []
    def generate(*args):
        calls.append(args)
        if len(calls) < 3:
            raise ProviderFailure("server_error", http_status=503)
        return {"rating": 1200, "tags": ["math"]}
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": "classification_v1", "max_attempts": 3, "request_interval": 0, "max_wait": 60}
    path = tmp_path / "run.json"
    manifest = reviewed_manifest()
    run = run_local(manifest, config, path, generate, max_requests=4, sleep=waits.append)
    assert len(calls) == 4 and len(run["predictions"]) == 2
    assert run["predictions"][reviewed_manifest()["items"][0]["key"]]["attempts"] == 3
    assert summarize_run(run, 12)["first_attempt_valid"] == 1
    assert summarize_run(run, 12)["pending"] == 10
    assert len(waits) == 2
    run_local(manifest, config, path, generate, max_requests=4, sleep=waits.append)
    assert len(calls) == 4


def test_managed_resume_recovers_capped_transient_not_invalid(reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local
    from api.ai_lab.contracts import ProviderFailure
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": "classification_v1", "max_attempts": 3, "request_interval": 0, "max_wait": 60}
    path = tmp_path / "run.json"
    manifest = reviewed_manifest()
    def fail(*args):
        raise ProviderFailure("timeout")
    run_local(manifest, config, path, fail, max_requests=1)
    run = run_local(manifest, config, path, lambda *a: {"rating": 850, "tags": ["fake"]},
                    max_requests=3, sleep=lambda seconds: None)
    assert run["request_count"] == 3
    assert len(run["predictions"]) == 2
    assert next(iter(run["predictions"].values()))["attempts"] == 2


@pytest.mark.parametrize("category,delay,reason", [("rate_limit", 86400, "provider_pause"),
                                                    ("authentication", None, "authentication"),
                                                    ("provider_error", None, "provider_error")])
def test_managed_stops_shared_failures_before_next_item(category, delay, reason, reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local
    from api.ai_lab.contracts import ProviderFailure
    def fail(*args):
        raise ProviderFailure(category, retry_after=delay)
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": "classification_v1", "max_attempts": 3, "request_interval": 0, "max_wait": 60}
    run = run_local(reviewed_manifest(), config, tmp_path / "run.json", fail, max_requests=60)
    assert run["request_count"] == 1
    assert run["stop_reason"] == reason


def test_explicit_recovery_preserves_history_and_never_starts_pending(reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local
    from api.ai_lab.contracts import ProviderFailure
    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "max_attempts": 1}
    def fail(*args):
        raise ProviderFailure("timeout")
    first = run_local(manifest, config, path, fail, max_requests=1)
    calls = []
    def success(*args):
        calls.append(args)
        return {"rating": 1200, "tags": ["math"], "justification": "synthetic"}
    recovered = run_local(manifest, config, path, success, max_requests=2, retry_failures=True)
    key = manifest["items"][0]["key"]
    assert len(calls) == 1 and len(recovered["predictions"]) == 1
    assert recovered["request_count"] == 2 and first["request_count"] == 1
    assert recovered["predictions"][key]["rating_status"] == "valid"
    history = recovered["attempt_history"][key]
    assert len(history) == 2 and history[0]["error"] == "timeout"
    assert history[1]["rating_status"] == "valid"
    run_local(manifest, config, path, success, max_requests=2, retry_failures=True)
    assert len(calls) == 1


def test_failure_history_keeps_safe_http_status(reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local
    from api.ai_lab.contracts import ProviderFailure
    manifest = reviewed_manifest()
    def fail(*args):
        raise ProviderFailure("server_error", http_status=503)
    result = run_local(manifest, {"provider": "fake", "model": "fake", "max_attempts": 1},
                       tmp_path / "run.json", fail, max_requests=1)
    key = manifest["items"][0]["key"]
    assert result["request_count"] == 1
    assert result["predictions"][key]["http_status"] == 503
    assert result["attempt_history"][key][0]["http_status"] == 503


def test_gemini_failure_keeps_safe_http_status():
    from unittest.mock import Mock
    from google.genai.errors import APIError
    from api.ai_lab.providers.gemini import generate
    from api.ai_lab.contracts import ProviderFailure
    client = Mock()
    client.models.generate_content.side_effect = APIError(503, {"error": {"message": "private-body"}})
    with pytest.raises(ProviderFailure) as failure:
        generate({}, "prompt", "gemini-3.5-flash-lite", client=client)
    assert failure.value.http_status == 503
    assert "private-body" not in str(failure.value)
    client.models.generate_content.assert_called_once()


@pytest.mark.parametrize("category", ["authentication", "provider_error", "parsing"])
def test_recovery_does_not_repeat_permanent_failures(category, reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local
    from api.ai_lab.contracts import ProviderFailure
    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "max_attempts": 1}
    def fail(*args):
        raise ProviderFailure(category, responded=category == "parsing")
    run_local(manifest, config, path, fail, max_requests=1)
    result = run_local(manifest, config, path, lambda *a: pytest.fail("must not call"),
                       max_requests=2, retry_failures=True)
    assert result["request_count"] == 1


def test_recovery_is_limited_per_item_and_respects_retry_after(reviewed_manifest, tmp_path, monkeypatch):
    from api.ai_lab import runner
    from api.ai_lab.contracts import ProviderFailure
    path = tmp_path / "run.json"
    manifest = reviewed_manifest()
    config = {"provider": "fake", "model": "fake", "max_attempts": 1}
    monkeypatch.setattr(runner.time, "time", lambda: 1000)
    def quota(*a):
        raise ProviderFailure("rate_limit", retry_after=120)
    runner.run_local(manifest, config, path, quota, max_requests=1)
    untouched = runner.run_local(manifest, config, path, lambda *a: pytest.fail("too early"),
                                 max_requests=2, retry_failures=True)
    assert untouched["request_count"] == 1
    monkeypatch.setattr(runner.time, "time", lambda: 1121)
    failed = runner.run_local(manifest, config, path, quota, max_requests=2, retry_failures=True)
    assert failed["request_count"] == 2
    monkeypatch.setattr(runner.time, "time", lambda: 1400)
    last = runner.run_local(manifest, config, path, lambda *a: pytest.fail("already recovered once"),
                            max_requests=3, retry_failures=True)
    assert last["request_count"] == 2


def test_exhausted_recovery_does_not_even_wait(reviewed_manifest, tmp_path, monkeypatch):
    from api.ai_lab import runner
    from api.ai_lab.contracts import ProviderFailure
    monkeypatch.setattr(runner.time, "time", lambda: 1000)
    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "max_attempts": 1}
    def quota(*a):
        raise ProviderFailure("rate_limit", retry_after=5)
    runner.run_local(manifest, config, path, quota, max_requests=1)
    run = runner.run_local(manifest, config, path, lambda *a: pytest.fail("no budget"), max_requests=1,
                           retry_failures=True, sleep=lambda seconds: pytest.fail("no budget for recovery"))
    assert run["request_count"] == 1


def test_normal_resume_respects_provider_pause_across_pending_items(reviewed_manifest, tmp_path, monkeypatch):
    from api.ai_lab import runner
    from api.ai_lab.contracts import ProviderFailure
    monkeypatch.setattr(runner.time, "time", lambda: 1000)
    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "max_attempts": 1}
    def quota(*a):
        raise ProviderFailure("rate_limit", retry_after=120)
    runner.run_local(manifest, config, path, quota, max_requests=1)
    result = runner.run_local(manifest, config, path, lambda *a: pytest.fail("provider is still paused"), max_requests=2)
    assert result["request_count"] == 1


@pytest.mark.parametrize("category", ["authentication", "provider_error", "rate_limit"])
def test_pilot_single_attempt_policy_stops_structural_or_quota_failure(category, reviewed_manifest, tmp_path):
    from api.ai_lab.contracts import ProviderFailure
    from api.ai_lab.runner import run_local

    calls = []

    def generate(*args):
        calls.append(args)
        raise ProviderFailure(category, retry_after=90 if category == "rate_limit" else None)

    manifest = reviewed_manifest()
    run = run_local(manifest, {"provider": "fake", "model": "fake", "max_attempts": 1},
                    tmp_path / "run.json", generate, max_requests=12)
    assert len(calls) == run["request_count"] == 1
    assert len(run["predictions"]) == 1


@pytest.mark.parametrize("rating,status", [(800, "valid"), (2400, "valid"), (2500, "out_of_domain"), (700, "out_of_domain"), (850, "invalid_output"), (True, "invalid_output"), (1200.0, "invalid_output"), ("1200", "invalid_output")])
def test_rating_domain_never_clamps(rating, status):
    from api.ai_lab.contracts import validate_prediction

    result = validate_prediction({"rating": rating, "tags": ["math"]})
    assert result["rating_status"] == status
    assert result["raw"]["rating"] == rating
    assert result["rating"] == (rating if status == "valid" else None)
    assert result["tags_status"] == "valid"


def test_tag_normalization_deduplicates_and_preserves_canonical_punctuation():
    from api.ai_lab.contracts import validate_prediction

    result = validate_prediction({"rating": 1400, "tags": [" MATH ", "binary   SEARCH", "math", "meet-in-the-middle"]})
    assert result["tags"] == ["binary search", "math", "meet-in-the-middle"]


@pytest.mark.parametrize("tags", [["dynamic programming"], ["dp", "fake"], [], "dp", [3], [""], None])
def test_invalid_tags_do_not_destroy_valid_rating(tags):
    from api.ai_lab.contracts import validate_prediction

    result = validate_prediction({"rating": 1600, "tags": tags})
    assert result["tags_status"] == "invalid_output"
    assert result["tags"] is None
    assert result["rating_status"] == "valid"


def test_taxonomy_includes_communication_from_official_catalog():
    from api.ai_lab.contracts import normalize_tags

    assert normalize_tags(["communication"]) == ["communication"]


def test_prompt_is_versioned_and_contains_domain_not_extra_statistics():
    from api.ai_lab.classification import load_prompt

    prompt = load_prompt()
    assert "800" in prompt and "2400" in prompt
    assert "total_solved" not in prompt
    assert "binary search" in prompt


@pytest.mark.parametrize("ratings,expected", [
    ([800, 900], 900), ([900, 1000], 1000), ([2300, 2400], 2400),
    ([800, 1000], 900), ([800, 900, 2400], 900), ([800], 800), ([2400], 2400),
])
def test_baseline_uses_model_rating_grid_with_half_up_ties(ratings, expected):
    from api.ai_lab.classification import median_baseline
    from api.ai_lab.contracts import validate_prediction

    rating = median_baseline(ratings)
    assert rating == expected
    assert type(rating) is int
    assert validate_prediction({"rating": rating, "tags": ["math"]})["rating_status"] == "valid"


def test_baseline_requires_development_ratings():
    from api.ai_lab.classification import median_baseline

    with pytest.raises(ValueError):
        median_baseline([])


def test_gemini_adapter_sends_separate_instruction_and_no_tools():
    from unittest.mock import MagicMock
    from api.ai_lab.providers.gemini import generate

    client = MagicMock()
    client.models.generate_content.return_value.parsed = {"rating": 1200, "tags": ["math"]}
    result = generate({"description": "Synthetic"}, "instructions", "gemini-3.5-flash-lite", client=client)
    assert result["rating"] == 1200
    call = client.models.generate_content.call_args.kwargs
    assert call["config"].system_instruction == "instructions"
    assert not call["config"].tools
    assert "Synthetic" in call["contents"]


def test_gemini_rate_limit_preserves_retry_after_without_exposing_error_body():
    from unittest.mock import MagicMock
    import httpx
    from google.genai.errors import APIError
    from api.ai_lab.providers.gemini import generate
    from api.ai_lab.contracts import ProviderFailure

    client = MagicMock()
    client.models.generate_content.side_effect = APIError(429, {"error": {"message": "sensitive-body"}},
                                                        response=httpx.Response(429, headers={"Retry-After": "120"}))
    with pytest.raises(ProviderFailure) as error:
        generate({}, "prompt", "model", client=client)
    assert error.value.retry_after == 120
    assert "sensitive-body" not in str(error.value)


@pytest.mark.parametrize("code,category", [(401, "authentication"), (500, "server_error")])
def test_gemini_classifies_provider_failures(code, category):
    from unittest.mock import MagicMock
    from google.genai.errors import APIError
    from api.ai_lab.providers.gemini import generate
    from api.ai_lab.contracts import ProviderFailure

    client = MagicMock()
    client.models.generate_content.side_effect = APIError(code, {"error": {"message": "failure"}})
    with pytest.raises(ProviderFailure, match=category):
        generate({}, "prompt", "model", client=client)


def test_gemini_records_usage_when_provided():
    from unittest.mock import MagicMock
    from types import SimpleNamespace
    from api.ai_lab.providers.gemini import generate

    client = MagicMock()
    client.models.generate_content.return_value = SimpleNamespace(
        parsed={"rating": 1200, "tags": ["math"]},
        usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5, total_token_count=20))
    result = generate({}, "prompt", "model", client=client)
    assert result["_usage"] == {"input_tokens": 10, "output_tokens": 5, "total_tokens": 20}


def test_local_runner_blocks_unreviewed_input_before_call(catalog, statement_html, tmp_path):
    from api.ai_lab.dataset import build_manifest
    from api.ai_lab.runner import run_local

    calls = []
    manifest = build_manifest(catalog, lambda url: statement_html)
    with pytest.raises(ValueError, match="review"):
        run_local(manifest, {"provider": "fake", "model": "fake"}, tmp_path / "run.json", lambda *args: calls.append(args))
    assert calls == []


def test_local_runner_saves_results_resumes_and_limits_retries(catalog, statement_html, tmp_path):
    import json
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest
    from api.ai_lab.contracts import ProviderFailure
    from api.ai_lab.runner import run_local

    manifest = build_manifest(catalog, lambda url: statement_html)
    for item in manifest["items"]:
        record_review(item, "mentor", "2026-10-17")
    freeze_manifest(manifest)
    count, sleeps = [], []
    def generate(*args):
        count.append(1)
        if len(count) < 3:
            raise ProviderFailure("rate_limit", retry_after=1)
        return {"rating": 1200, "tags": ["math"]}
    path = tmp_path / "run.json"
    run = run_local(manifest, {"provider": "fake", "model": "fake"}, path, generate, sleep=sleeps.append)
    assert len(count) == 14 and sleeps == [1, 1]
    assert len(run["predictions"]) == 12
    assert json.loads(path.read_text())["dataset_hash"] == manifest["hash"]
    assert run["predictions"][manifest["items"][0]["key"]]["attempts"] == 3
    run_local(manifest, {"provider": "fake", "model": "fake"}, path, generate)
    assert len(count) == 14
    with pytest.raises(ValueError, match="configuration"):
        run_local(manifest, {"provider": "fake", "model": "other"}, path, generate)


def test_retry_after_too_long_does_not_retry_early(catalog, statement_html, tmp_path):
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest
    from api.ai_lab.contracts import ProviderFailure
    from api.ai_lab.runner import run_local

    manifest = build_manifest(catalog, lambda url: statement_html)
    for item in manifest["items"]:
        record_review(item, "mentor", "2026-10-17")
    freeze_manifest(manifest)
    calls, sleeps = [], []
    def generate(*args):
        calls.append(1)
        raise ProviderFailure("rate_limit", retry_after=120)
    run = run_local(manifest, {"provider": "fake", "model": "fake"}, tmp_path / "run.json", generate, sleep=sleeps.append)
    assert len(calls) == 12 and not sleeps
    assert all(p["rating_status"] == "transport_error" for p in run["predictions"].values())


def test_request_cap_counts_retries_and_persists_across_resume(catalog, statement_html, tmp_path):
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest
    from api.ai_lab.runner import run_local
    from api.ai_lab.contracts import ProviderFailure

    manifest = build_manifest(catalog, lambda url: statement_html)
    for item in manifest["items"]:
        record_review(item, "mentor", "2026-10-17")
    freeze_manifest(manifest)
    calls = []
    def generate(*args):
        calls.append(1)
        raise ProviderFailure("rate_limit", retry_after=0)
    path = tmp_path / "run.json"
    run = run_local(manifest, {"provider": "fake", "model": "fake"}, path, generate, max_requests=2)
    assert len(calls) == 2
    assert run["request_count"] == 2
    run_local(manifest, {"provider": "fake", "model": "fake"}, path, generate, max_requests=2)
    assert len(calls) == 2


def test_authorized_limit_can_grow_without_changing_scientific_config(reviewed_manifest, tmp_path):
    import json
    from api.ai_lab.runner import run_local

    calls = []
    path = tmp_path / "run.json"
    manifest = reviewed_manifest()
    config = {"provider": "fake", "model": "fake"}
    def generate(*args):
        saved = json.loads(path.read_text())
        assert saved["request_count"] == len(calls) + 1
        assert saved["authorized_request_limit"] == (2 if len(calls) < 2 else 5)
        calls.append(1)
        return {"rating": 1200, "tags": ["math"]}
    first = run_local(manifest, config, path, generate, max_requests=2)
    assert first["request_count"] == 2 and len(calls) == 2
    science = first["configuration"].copy()
    assert "max_requests" not in science
    assert "authorized_request_limit" not in science
    same = run_local(manifest, config, path, generate, max_requests=2)
    assert same["request_count"] == 2 and len(calls) == 2
    grown = run_local(manifest, config, path, generate, max_requests=5)
    assert grown["request_count"] == 5 and len(calls) == 5
    assert grown["configuration"] == science
    assert grown["authorized_request_limit"] == 5
    with pytest.raises(ValueError, match="limit|cap"):
        run_local(manifest, config, path, generate, max_requests=4)


def test_crash_after_increment_preserves_spent_budget_and_rejects_lower_authorization(reviewed_manifest, tmp_path):
    import json
    from api.ai_lab.runner import run_local

    manifest = reviewed_manifest()
    path = tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake"}
    def crash(*args):
        assert json.loads(path.read_text())["request_count"] == 1
        raise RuntimeError("simulated crash after persisted increment")
    with pytest.raises(RuntimeError, match="Unexpected benchmark error"):
        run_local(manifest, config, path, crash, max_requests=5)
    assert json.loads(path.read_text())["request_count"] == 1
    with pytest.raises(ValueError, match="limit|cap"):
        run_local(manifest, config, path, crash, max_requests=4)
    calls = []
    def generate(*args):
        calls.append(1)
        return {"rating": 1200, "tags": ["math"]}
    resumed = run_local(manifest, config, path, generate, max_requests=5)
    assert resumed["request_count"] == 5
    assert len(calls) == 4


def test_interrupted_item_is_not_silently_called_again_on_resume(reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local

    manifest, path = reviewed_manifest(), tmp_path / "run.json"
    config = {"provider": "fake", "model": "fake", "max_attempts": 1}
    first_input = manifest["items"][0]["input"]
    # Fixture inputs are identical: distinguish the first item's call by object identity.
    def crash(*args):
        raise RuntimeError("response not persisted")
    with pytest.raises(RuntimeError):
        run_local(manifest, config, path, crash, max_requests=2)
    called = []
    def generate(prepared, *args):
        called.append(prepared)
        return {"rating": 1200, "tags": ["math"]}
    resumed = run_local(manifest, config, path, generate, max_requests=2)
    assert len(called) == 1 and called[0] is not first_input
    key = manifest["items"][0]["key"]
    assert resumed["predictions"][key]["error"] == "interrupted"
    assert resumed["request_count"] == 2
    recovered = run_local(manifest, config, path, lambda *a: pytest.fail("unknown outcome cannot be retried"),
                          max_requests=3, retry_failures=True)
    assert recovered["request_count"] == 2


@pytest.mark.parametrize("change", ["model", "provider", "prompt", "dataset"])
def test_budget_growth_does_not_allow_scientific_changes(change, reviewed_manifest, tmp_path, monkeypatch):
    import json
    import api.ai_lab.runner as runner
    from api.ai_lab.dataset import content_hash

    path = tmp_path / "run.json"
    manifest = reviewed_manifest()
    config = {"provider": "fake", "model": "fake"}
    generate = lambda *args: {"rating": 1200, "tags": ["math"]}
    runner.run_local(manifest, config, path, generate, max_requests=2)
    before = json.loads(path.read_text())
    if change in ("model", "provider"):
        config[change] = "changed"
    elif change == "prompt":
        monkeypatch.setattr(runner, "load_prompt", lambda: "changed prompt")
    else:
        manifest["seed"] = 99
        manifest["hash"] = content_hash({k: v for k, v in manifest.items() if k != "hash"})
    with pytest.raises(ValueError, match="configuration"):
        runner.run_local(manifest, config, path, generate, max_requests=5)
    assert json.loads(path.read_text()) == before
