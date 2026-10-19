import json

import pytest


def test_private_examples_render_exactly_four_blocks_without_source_identifiers(few_shot_context):
    from api.ai_lab.classification import load_prompt
    development, evaluation, path, artifact = few_shot_context
    prompt = load_prompt("classification_v3", examples_path=path, development=development, evaluation=evaluation)
    assert prompt.count("<example>") == 4
    assert "{examples}" not in prompt and "{taxonomy}" not in prompt
    assert '"key":' not in prompt and '"development_hash":' not in prompt
    for item in artifact["examples"]:
        assert json.dumps(item["output"], ensure_ascii=False) in prompt


@pytest.mark.parametrize("corruption", ["count", "duplicate", "input", "rating", "tags", "justification", "extra", "hash"])
def test_unreviewed_or_incompatible_examples_fail_before_render(corruption, few_shot_context):
    from api.ai_lab.classification import load_prompt
    development, evaluation, path, artifact = few_shot_context
    if corruption == "count":
        artifact["examples"].pop()
    elif corruption == "duplicate":
        artifact["examples"][1] = artifact["examples"][0]
    elif corruption == "input":
        artifact["examples"][0]["input"]["description"] = "Unreviewed modification"
    elif corruption == "hash":
        artifact["development_hash"] = "changed"
    elif corruption == "extra":
        artifact["examples"][0]["output"]["private"] = "extra field"
    else:
        artifact["examples"][0]["output"][corruption] = {"rating": 850, "tags": ["fake"], "justification": ""}[corruption]
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError):
        load_prompt("classification_v3", examples_path=path, development=development, evaluation=evaluation)


def test_examples_cannot_be_evaluated_on_their_own_dataset(few_shot_context):
    from api.ai_lab.classification import load_prompt
    development, _, path, _ = few_shot_context
    with pytest.raises(ValueError, match="overlap"):
        load_prompt("classification_v3", examples_path=path, development=development, evaluation=development)


def test_completed_few_shot_run_is_resumable_and_examples_changes_are_rejected(few_shot_context, tmp_path):
    from api.ai_lab.runner import run_local
    development, evaluation, examples_path, artifact = few_shot_context
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": "classification_v3", "max_attempts": 3, "request_interval": 0, "max_wait": 60}
    calls = []
    def generate(*args):
        calls.append(args)
        return {"rating": 1200, "tags": ["math"]}
    path = tmp_path / "run.json"
    first = run_local(evaluation, config, path, generate, max_requests=1,
                      examples_path=examples_path, development=development)
    run_local(evaluation, config, path, generate, max_requests=1,
              examples_path=examples_path, development=development)
    assert len(calls) == 1 and first["configuration"]["examples_hash"]
    assert calls[0][1].count("<example>") == 4
    artifact["examples"][0]["output"]["justification"] = "Another reviewed explanation"
    examples_path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="configuration"):
        run_local(evaluation, config, path, generate, max_requests=2,
                  examples_path=examples_path, development=development)
    assert len(calls) == 1


@pytest.mark.parametrize("provider,model,key_env", [("groq", "openai/gpt-oss-20b", "GROQ_API_KEY"),
                                                  ("gemini", "gemini-3.5-flash-lite", "GEMINI_API_KEY")])
def test_command_passes_private_examples_to_selected_adapter(provider, model, key_env, few_shot_context, tmp_path, monkeypatch):
    from django.core.management import call_command
    from api.ai_lab.runner import save_json
    from api.management.commands import run_ai_benchmark as command
    development, evaluation, path, _ = few_shot_context
    root = tmp_path
    save_json(root / "datasets/cf-rating-v1/development/manifest.json", development)
    save_json(root / "datasets/cf-rating-v1/final/manifest.json", evaluation)
    monkeypatch.setattr(command, "guarded_root", lambda options: root)
    monkeypatch.setenv("AI_LAB_FREE_TIER_CONFIRMED", "true")
    monkeypatch.setenv(key_env, "synthetic-key")
    calls = []
    def generate(prepared, prompt, selected):
        calls.append(selected)
        assert prompt.count("<example>") == 4
        return {"rating": 1200, "tags": ["math"]}
    monkeypatch.setattr(command, "get_generator", lambda *a: generate)
    call_command("run_ai_benchmark", classifier=provider, model=model, allow_model=model,
                 run_id="fewshot-synthetic", split="final", prompt="classification_v3",
                 examples_file=str(path), max_requests=1, request_interval=0)
    run = json.loads((root / "runs/fewshot-synthetic/run.json").read_text())
    assert calls == [model]
    assert run["configuration"]["examples_hash"]


def test_cli_rejects_examples_outside_private_root_before_model_resolution(tmp_path, monkeypatch):
    from django.core.management import call_command, CommandError
    from api.management.commands import run_ai_benchmark as command
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path / "private")
    monkeypatch.setattr(command, "get_generator", lambda *a: pytest.fail("must not resolve model"))
    with pytest.raises(CommandError, match="private JSON"):
        call_command("run_ai_benchmark", classifier="groq", prompt="classification_v3", examples_file=str(tmp_path / "outside.json"))
