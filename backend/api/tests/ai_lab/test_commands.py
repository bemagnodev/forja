"""CLI responsibilities justify a separate file; legacy tests stay in place."""
import pytest
from django.core.management import call_command, CommandError


def test_status_reads_saved_progress_without_keys_or_generator(reviewed_manifest, tmp_path, monkeypatch, capsys):
    from api.ai_lab.runner import save_json
    from api.management.commands import run_ai_benchmark as command
    manifest = reviewed_manifest()
    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", manifest)
    save_json(tmp_path / "runs/synthetic/run.json", {"dataset_hash": manifest["hash"],
              "predictions": {}, "request_count": 0, "authorized_request_limit": 60})
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setattr(command, "get_generator", lambda *a: pytest.fail("status must never infer"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    call_command("run_ai_benchmark", status=True, run_id="synthetic")
    assert '"pending": 12' in capsys.readouterr().out


@pytest.mark.parametrize("name", ["prepare_ai_dataset", "validate_ai_dataset", "run_ai_benchmark"])
def test_dataset_version_is_explicit_and_django_version_never_does_io(name, monkeypatch, capsys):
    from django import get_version
    from django.core.management import load_command_class
    command = load_command_class("api", name)
    parser = command.create_parser("manage.py", name)
    assert parser.parse_args(["--dataset-version", "v2"]).dataset_version == "v2"
    with pytest.raises(SystemExit) as exit:
        parser.parse_args(["--version"])
    assert exit.value.code == 0
    assert get_version() in capsys.readouterr().out


@pytest.mark.parametrize("command", ["prepare_ai_dataset", "validate_ai_dataset", "run_ai_benchmark"])
def test_real_commands_reject_test_settings_before_network(command):
    with pytest.raises(CommandError, match="local"):
        call_command(command, settings="core.settings_test")


def test_prepare_command_writes_private_snapshot_and_review_artifacts(catalog, statement_html, tmp_path, monkeypatch):
    from api.management.commands import prepare_ai_dataset as command

    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setattr(command, "fetch_catalog", lambda: catalog)
    monkeypatch.setattr(command, "fetch_html", lambda url: statement_html)
    call_command("prepare_ai_dataset")
    import json
    manifest = json.loads((tmp_path / "datasets/cf-rating-v1/development/manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["items"]) == 12
    assert (tmp_path / "datasets/cf-rating-v1/development/review.html").exists()
    assert len(list((tmp_path / "datasets/cf-rating-v1/development/raw").glob("*.html"))) == 12


def test_freeze_command_never_auto_approves_items(catalog, statement_html, tmp_path, monkeypatch):
    from api.ai_lab.dataset import build_manifest
    from api.ai_lab.runner import save_json
    from api.management.commands import validate_ai_dataset as command

    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    path = tmp_path / "datasets/cf-rating-v1/development/manifest.json"
    save_json(path, build_manifest(catalog, lambda url: statement_html))
    with pytest.raises(CommandError, match="review"):
        call_command("validate_ai_dataset", freeze=True)


def test_local_settings_rejects_missing_explicit_sqlite(monkeypatch):
    import runpy
    from pathlib import Path

    monkeypatch.delenv("AI_LAB_SQLITE_PATH", raising=False)
    with pytest.raises(ValueError, match="AI_LAB_SQLITE_PATH"):
        runpy.run_path(str(Path(__file__).parents[3] / "core/settings_ai_lab_local.py"))


def test_baseline_command_runs_without_api_key(catalog, statement_html, tmp_path, monkeypatch):
    import json
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest
    from api.ai_lab.runner import save_json
    from api.management.commands import run_ai_benchmark as command

    manifest = build_manifest(catalog, lambda url: statement_html)
    for item in manifest["items"]:
        record_review(item, "mentor", "2026-10-17")
    freeze_manifest(manifest)
    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", manifest)
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    call_command("run_ai_benchmark", classifier="baseline", run_id="baseline-v1")
    report = json.loads((tmp_path / "runs/baseline-v1/metrics.json").read_text())
    assert report["runs"]["baseline-v1"]["rating_coverage"] == 1
    assert report["runs"]["baseline-v1"]["tags_micro_f1"] is None
    run = json.loads((tmp_path / "runs/baseline-v1/run.json").read_text())
    assert run["configuration"]["model"] == "development-median-grid100-half-up-v2"


def test_real_model_command_requires_free_tier_confirmation(catalog, statement_html, tmp_path, monkeypatch):
    from api.ai_lab.dataset import build_manifest
    from api.ai_lab.runner import save_json
    from api.management.commands import run_ai_benchmark as command

    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", build_manifest(catalog, lambda url: statement_html))
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.delenv("AI_LAB_FREE_TIER_CONFIRMED", raising=False)
    with pytest.raises(CommandError, match="free-tier"):
        call_command("run_ai_benchmark", classifier="gemini")


def test_model_execution_requires_exact_authorization_and_request_cap(catalog, statement_html, tmp_path, monkeypatch):
    from api.ai_lab.dataset import build_manifest
    from api.ai_lab.runner import save_json
    from api.management.commands import run_ai_benchmark as command

    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", build_manifest(catalog, lambda url: statement_html))
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setenv("AI_LAB_FREE_TIER_CONFIRMED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-real-key")
    with pytest.raises(CommandError, match="authorization"):
        call_command("run_ai_benchmark", classifier="gemini", model="gemini-3.5-flash-lite")


def test_default_classifier_is_local_baseline():
    from api.management.commands.run_ai_benchmark import Command

    options = Command().create_parser("manage.py", "run_ai_benchmark").parse_args([])
    assert options.classifier == "baseline"
    assert options.model is None


def test_new_gemini_run_records_managed_policy(reviewed_manifest, tmp_path, monkeypatch):
    import json
    from api.ai_lab.runner import save_json
    from api.ai_lab.providers import gemini
    from api.management.commands import run_ai_benchmark as command
    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", reviewed_manifest())
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setenv("AI_LAB_FREE_TIER_CONFIRMED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key")
    monkeypatch.setattr(gemini, "generate", lambda *a: {"rating": 1200, "tags": ["math"]})
    call_command("run_ai_benchmark", classifier="gemini", model="gemini-3.5-flash-lite",
                 allow_model="gemini-3.5-flash-lite", max_requests=1, run_id="new-policy")
    run = json.loads((tmp_path / "runs/new-policy/run.json").read_text(encoding="utf-8"))
    assert run["configuration"]["max_attempts"] == 3
    assert run["configuration"]["execution_policy"] == "managed-v1"
    assert run["configuration"]["prompt_version"] == "classification_v1"


def test_snapshot_export_is_read_only_without_model_authorization(tmp_path, monkeypatch):
    from api.ai_lab import results
    from api.management.commands import run_ai_benchmark as command
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    calls = []
    monkeypatch.setattr(results, "export_snapshot", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(command, "get_generator", lambda *a: pytest.fail("export cannot resolve model"))
    call_command("run_ai_benchmark", export_showcase="pilot-v1")
    assert calls[0][0] == (tmp_path, "pilot-v1", tmp_path / "exports/pilot-v1.json")
    with pytest.raises(CommandError, match="export"):
        call_command("run_ai_benchmark", export_showcase="pilot-v1", model="openai/gpt-oss-120b")


@pytest.mark.parametrize("model", ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"])
def test_groq_command_uses_exact_model_budget_and_shared_contract(model, reviewed_manifest, tmp_path, monkeypatch):
    import json
    from api.ai_lab.runner import save_json
    from api.ai_lab.providers import groq
    from api.management.commands import run_ai_benchmark as command

    manifest = reviewed_manifest()
    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", manifest)
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setenv("AI_LAB_FREE_TIER_CONFIRMED", "true")
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-key")
    calls = []

    def generate(prepared, prompt, selected):
        calls.append(selected)
        return {"rating": 1200, "tags": ["math"], "justification": "Synthetic"}

    monkeypatch.setattr(groq, "generate", generate)
    call_command("run_ai_benchmark", classifier="groq", model=model, allow_model=model,
                 max_requests=2, run_id="groq-synthetic")
    run = json.loads((tmp_path / "runs/groq-synthetic/run.json").read_text())
    assert calls == [model, model]
    assert run["configuration"]["provider"] == "groq"
    expected_generation = {"reasoning_effort": "low", "max_completion_tokens": 4096}
    if model == "qwen/qwen3.8-27b":
        expected_generation["reasoning_format"] = "hidden"
    assert run["configuration"]["generation"] == expected_generation
    assert run["configuration"]["max_attempts"] == 3
    assert run["request_count"] == 2
    call_command("run_ai_benchmark", classifier="groq", model=model, allow_model=model,
                 max_requests=2, run_id="groq-synthetic")
    assert len(calls) == 2


def test_catalog_rejects_provider_mismatch_and_unknown_models():
    from api.ai_lab.catalog import get_model

    assert get_model("groq", "qwen/qwen3.8-27b")["key_env"] == "GROQ_API_KEY"
    with pytest.raises(ValueError, match="model"):
        get_model("groq", "gemini-3.5-flash-lite")
    with pytest.raises(ValueError, match="model"):
        get_model("groq", "paid-or-unknown")


def test_versions_coexist_and_same_split_cannot_be_overwritten(mock_collection):
    import json

    root = mock_collection
    call_command("prepare_ai_dataset", dataset_version="v1")
    first = root / "datasets/v1/development/manifest.json"
    before = first.read_bytes()
    call_command("prepare_ai_dataset", dataset_version="v2")
    assert first.read_bytes() == before
    assert json.loads(before)["version"] == "v1"
    assert json.loads((root / "datasets/v2/development/manifest.json").read_text())["version"] == "v2"
    with pytest.raises(CommandError, match="already exists"):
        call_command("prepare_ai_dataset", dataset_version="v1")
    assert first.read_bytes() == before


@pytest.mark.parametrize("version", ["", "..", "v..1", "v/a", "v\\a", "/absolute", "C:\\absolute", "bad?", "_bad", "v" * 65])
@pytest.mark.parametrize("command_name", ["prepare_ai_dataset", "validate_ai_dataset", "run_ai_benchmark"])
def test_unsafe_version_rejected_before_io(command_name, version, monkeypatch):
    import importlib

    command = importlib.import_module(f"api.management.commands.{command_name}")
    monkeypatch.setattr(command, "guarded_root", lambda options: pytest.fail("version must be checked before I/O"))
    with pytest.raises(CommandError, match="version"):
        call_command(command_name, dataset_version=version)


def test_validation_changes_only_requested_version(reviewed_manifest, tmp_path, monkeypatch):
    from api.ai_lab.runner import save_json
    from api.management.commands import validate_ai_dataset as command

    first = tmp_path / "datasets/v1/development/manifest.json"
    second = tmp_path / "datasets/v2/development/manifest.json"
    save_json(first, reviewed_manifest("v1"))
    save_json(second, reviewed_manifest("v2"))
    before = first.read_bytes()
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    call_command("validate_ai_dataset", dataset_version="v2")
    assert first.read_bytes() == before
    assert not (first.parent / "validation.json").exists()
    assert (second.parent / "validation.json").exists()


def test_benchmark_reads_only_requested_version(reviewed_manifest, tmp_path, monkeypatch):
    import json
    from api.ai_lab.runner import save_json
    from api.management.commands import run_ai_benchmark as command

    save_json(tmp_path / "datasets/v1/development/manifest.json", reviewed_manifest("v1"))
    selected = reviewed_manifest("v2")
    save_json(tmp_path / "datasets/v2/development/manifest.json", selected)
    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    call_command("run_ai_benchmark", dataset_version="v2", classifier="baseline", run_id="selected-v2")
    run = json.loads((tmp_path / "runs/selected-v2/run.json").read_text())
    assert run["dataset_hash"] == selected["hash"]


def test_final_requires_frozen_development_of_same_version(reviewed_manifest, mock_collection, monkeypatch):
    from api.ai_lab.runner import save_json
    from api.management.commands import prepare_ai_dataset as command

    save_json(mock_collection / "datasets/v1/development/manifest.json", reviewed_manifest("v1"))
    monkeypatch.setattr(command, "fetch_catalog", lambda: pytest.fail("must reject before HTTP"))
    with pytest.raises(CommandError, match="development"):
        call_command("prepare_ai_dataset", dataset_version="v2", split="final")
    wrong = reviewed_manifest("v1")
    save_json(mock_collection / "datasets/v2/development/manifest.json", wrong)
    with pytest.raises(CommandError, match="version"):
        call_command("prepare_ai_dataset", dataset_version="v2", split="final")
    wrong = reviewed_manifest("v2")
    wrong["state"] = "collected"
    save_json(mock_collection / "datasets/v2/development/manifest.json", wrong)
    with pytest.raises(CommandError, match="freez|review"):
        call_command("prepare_ai_dataset", dataset_version="v2", split="final")


def test_versioned_review_remains_under_ignored_private_root(mock_collection):
    import subprocess
    from pathlib import Path

    call_command("prepare_ai_dataset", dataset_version="review-v1")
    relative = "backend/var/ai_lab/datasets/review-v1/development/review.html"
    repo = Path(__file__).resolve().parents[4]
    result = subprocess.run(["git", "check-ignore", "--no-index", relative], cwd=repo, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == relative
    assert (mock_collection / "datasets/review-v1/development/review.html").exists()
