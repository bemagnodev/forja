"""Read-only showcase: private artifacts in, explicit public fields out."""
import json

import pytest


def test_full_dataset_tag_policy_is_exported_and_scores_raw_unknown_labels(showcase, tmp_path):
    from api.ai_lab.results import export_snapshot, read_snapshot
    from api.ai_lab.runner import save_json
    root, manifest = showcase
    index = json.loads((root / "showcase.json").read_text(encoding="utf-8"))
    index["benchmarks"][0]["tag_scoring"] = "full-dataset-v1"
    save_json(root / "showcase.json", index)
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    key = manifest["items"][0]["key"]
    run["predictions"][key].update(tags=None, tags_status="invalid_output", raw={"tags": ["unknown"]})
    save_json(path, run)
    output = tmp_path / "public/pilot-v1.json"
    export_snapshot(root, "pilot-v1", output)
    data = read_snapshot(output.parent, "pilot-v1")
    assert data["tag_scoring"] == "full-dataset-v1"
    assert len(data["intersections"]["tags"]) == 12
    model = next(r for r in data["runs"] if r["provider"] != "baseline")
    assert model["metrics"]["tags_micro_f1"] == pytest.approx(22 / 24)
    assert model["metrics"]["tags_false_positive"] == 1
    assert model["metrics"]["tags_false_negative"] == 1
    assert model["metrics"]["tags_evaluated"] == 12
    assert '"raw"' not in output.read_text(encoding="utf-8")


def test_curated_snapshots_have_three_comparisons_and_no_private_examples():
    from pathlib import Path
    from api.ai_lab.results import list_snapshots, read_snapshot
    root = Path(__file__).resolve().parents[2] / "ai_lab/published"
    selected = list_snapshots(root)
    assert [item["label"] for item in selected] == ["1. Modelos", "2. Prompts", "3. Raciocínio"]
    models, prompts, thinking = [read_snapshot(root, item["id"]) for item in selected]
    assert len(models["intersections"]["rating"]) == 60
    assert len(prompts["intersections"]["rating"]) == 60
    assert len(thinking["intersections"]["rating"]) == 59
    assert len(thinking["intersections"]["tags"]) == 60
    assert any(run["id"] == "cf60-gpt20-a-v1-recovered-524d" for run in models["runs"])
    reference_baseline = {p["key"]: p["predictions"]["cf60-baseline-grid100-v2"] for p in models["problems"]}
    for comparison in (models, prompts, thinking):
        assert comparison["tag_scoring"] == "full-dataset-v1"
        assert len(comparison["intersections"]["tags"]) == 60
        assert comparison["dataset"]["version"] == "cf-rating-v1"
        baselines = [run for run in comparison["runs"] if run["provider"] == "baseline"]
        assert len(baselines) == 1
        baseline = baselines[0]
        assert baseline["id"] == "cf60-baseline-grid100-v2"
        assert baseline["metrics"]["rating_valid"] == 60
        assert baseline["metrics"]["tags_micro_f1"] is None
        assert baseline["generation_attempts"] == 0
        assert {p["key"]: p["predictions"][baseline["id"]] for p in comparison["problems"]} == reference_baseline
        errors = [abs(reference_baseline[p["key"]]["rating"] - p["reference"]["rating"])
                  for p in comparison["problems"] if p["key"] in comparison["intersections"]["rating"]]
        assert baseline["metrics"]["mae"] == pytest.approx(sum(errors) / len(errors))
        for model in (run for run in comparison["runs"] if run["provider"] != "baseline"):
            metrics = model["metrics"]
            assert metrics["tags_evaluated"] == 60
            tp, fp, fn = (metrics[key] for key in ("tags_true_positive", "tags_false_positive", "tags_false_negative"))
            assert metrics["tags_micro_f1"] == pytest.approx(2 * tp / (2 * tp + fp + fn))
    a_models = next(r for r in models["runs"] if r["id"] == "cf60-gemini35-a-v1")
    a_prompts = next(r for r in prompts["runs"] if r["id"] == "cf60-gemini35-a-v1")
    assert a_models["metrics"] == a_prompts["metrics"]
    assert [run["label"] for run in prompts["runs"] if run["provider"] != "baseline"] == ["A · Direto", "B · Rubrica", "C · Exemplos"]
    private = next(p for p in prompts["prompts"] if p["version"] == "classification_v3")
    assert private["private_examples"] and "text" not in private
    assert {r["parameters"]["thinking_level"] for r in thinking["runs"] if r["provider"] != "baseline"} == {"minimal", "high"}
    assert all(r["token_usage"]["items_with_usage"] == 59 for r in thinking["runs"] if r["provider"] != "baseline")


def test_published_index_curates_order_and_hides_other_files(showcase, tmp_path):
    from api.ai_lab.results import export_snapshot, list_snapshots, read_snapshot
    from api.ai_lab.runner import save_json
    root, _ = showcase
    published = tmp_path / "published"
    export_snapshot(root, "pilot-v1", published / "pilot-v1.json")
    index = json.loads((root / "showcase.json").read_text(encoding="utf-8"))
    index["benchmarks"].append({**index["benchmarks"][0], "id": "z-first"})
    save_json(root / "showcase.json", index)
    export_snapshot(root, "z-first", published / "z-first.json")
    (published / "irrelevant.json").write_text("broken archive", encoding="utf-8")
    save_json(published / "index.json", {"benchmarks": ["z-first", "pilot-v1"]})
    assert [r["id"] for r in list_snapshots(published)] == ["z-first", "pilot-v1"]
    with pytest.raises(LookupError):
        read_snapshot(published, "irrelevant")
    save_json(published / "index.json", {"benchmarks": []})
    assert list_snapshots(published) == []
    with pytest.raises(LookupError):
        read_snapshot(published, "pilot-v1")


@pytest.mark.parametrize("ids", [["pilot-v1", "pilot-v1"], ["../archive"], "pilot-v1"])
def test_published_index_rejects_invalid_selection(ids, tmp_path):
    from api.ai_lab.results import list_snapshots
    from api.ai_lab.runner import save_json
    save_json(tmp_path / "index.json", {"benchmarks": ids})
    with pytest.raises(ValueError):
        list_snapshots(tmp_path)


def test_reviewed_prompt_export_uses_recorded_text_and_deduplicates(showcase, tmp_path, monkeypatch):
    from api.ai_lab.results import export_snapshot, read_snapshot
    from api.ai_lab.runner import save_json
    root, _ = showcase
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    run["configuration"]["prompt_version"] = "classification_v1"
    recorded = run["configuration"]["prompt"]
    save_json(path, run)
    save_json(root / "runs/model-b/run.json", run)
    index = json.loads((root / "showcase.json").read_text(encoding="utf-8"))
    entry = index["benchmarks"][0]
    entry.update(publish_prompts=True, selection_note="Critério revisado")
    entry["runs"].append("model-b")
    save_json(root / "showcase.json", index)
    monkeypatch.setattr("api.ai_lab.classification.load_prompt", lambda *a: pytest.fail("Use recorded prompt"))
    output = tmp_path / "public/pilot-v1.json"
    export_snapshot(root, "pilot-v1", output)
    data = read_snapshot(output.parent, "pilot-v1")
    assert len(data["prompts"]) == 1
    assert data["dataset"]["version"] == "cf-rating-v1"
    prompt = data["prompts"][0]
    assert prompt["text"] == recorded and "{taxonomy}" not in prompt["text"]
    assert prompt["hash"] == run["configuration"]["prompt_hash"]
    assert prompt["label"] == "Classificação direta"
    assert data["selection_note"] == "Critério revisado"
    assert "PRIVATE" not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("version,text", [("classification_v3", "PRIVATE-EXAMPLES"),
                                         ("classification_v1", "modified unreviewed prompt")])
def test_prompt_publication_requires_reviewed_version_and_hash(showcase, version, text):
    from api.ai_lab.results import read_benchmark
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.runner import save_json
    root, _ = showcase
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    run["configuration"].update(prompt_version=version, prompt=text, prompt_hash=content_hash(text))
    save_json(path, run)
    index = json.loads((root / "showcase.json").read_text(encoding="utf-8"))
    index["benchmarks"][0]["publish_prompts"] = True
    save_json(root / "showcase.json", index)
    with pytest.raises(ValueError, match="reviewed prompt"):
        read_benchmark(root, "pilot-v1")


def test_prompt_comparison_is_explicit_and_labels_each_configuration(showcase):
    from api.ai_lab.results import read_benchmark
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.runner import save_json
    root, _ = showcase
    run = json.loads((root / "runs/model-a/run.json").read_text())
    run["configuration"].update(prompt="synthetic examples", prompt_hash=content_hash("synthetic examples"),
                                prompt_version="classification_v2")
    save_json(root / "runs/model-b/run.json", run)
    index = json.loads((root / "showcase.json").read_text())
    index["benchmarks"][0]["runs"].append("model-b")
    save_json(root / "showcase.json", index)
    with pytest.raises(ValueError, match="prompt"):
        read_benchmark(root, "pilot-v1")
    index["benchmarks"][0]["compare_prompts"] = True
    save_json(root / "showcase.json", index)
    result = read_benchmark(root, "pilot-v1")
    assert "Classificação com rubrica" in result["runs"][-1]["label"]
    assert result["runs"][-1]["strategy_label"] == "Classificação com rubrica"
    assert result["prompt"]["hash"] is None


@pytest.fixture
def showcase(tmp_path, reviewed_manifest, settings):
    from api.ai_lab.classification import baseline_predictions, load_prompt
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.runner import save_json

    settings.AI_LAB_RESULTS_ROOT = tmp_path
    settings.AI_LAB_USE_PRIVATE_RESULTS = True
    manifest = reviewed_manifest()
    save_json(tmp_path / "datasets/cf-rating-v1/development/manifest.json", manifest)
    save_json(tmp_path / "showcase.json", {"benchmarks": [{
        "id": "pilot-v1", "label": "Piloto v1", "version": "cf-rating-v1", "split": "development",
        "runs": ["baseline", "model-a"],
    }]})
    save_json(tmp_path / "runs/baseline/run.json", {
        "dataset_hash": manifest["hash"], "configuration": {"provider": "baseline", "model": "median"},
        "predictions": baseline_predictions(manifest, manifest),
    })
    predictions = {item["key"]: {
        "rating": item["reference"]["rating"] + 100, "rating_status": "valid",
        "tags": ["math"], "tags_status": "valid", "responded": True, "duration": 1,
        "justification": "Synthetic justification", "attempts": 1,
        "raw": {"secret": "PRIVATE-RESPONSE"},
    } for item in manifest["items"]}
    save_json(tmp_path / "runs/model-a/run.json", {
        "dataset_hash": manifest["hash"], "configuration": {
            "provider": "gemini", "model": "gemini-3.5-flash-lite",
            "prompt": load_prompt(), "prompt_hash": content_hash(load_prompt()),
            "private": "PRIVATE-CONFIG",
        }, "predictions": predictions, "request_count": 12,
    })
    return tmp_path, manifest


@pytest.mark.django_db
def test_showcase_requires_authentication(client, showcase):
    assert client.get("/api/ai-lab/benchmarks").status_code == 401
    assert client.get("/api/ai-lab/benchmarks/pilot-v1").status_code == 401


@pytest.mark.django_db
def test_saved_comparison_is_paired_sanitized_and_read_only(api_client, showcase, monkeypatch):
    from api.ai_lab.providers import gemini, groq

    monkeypatch.setattr(gemini, "generate", lambda *a: pytest.fail("GET cannot call AI"))
    monkeypatch.setattr(groq, "generate", lambda *a: pytest.fail("GET cannot call AI"))
    root, manifest = showcase
    before = {p: p.read_bytes() for p in root.rglob("*.json")}
    listing = api_client.get("/api/ai-lab/benchmarks")
    assert listing.status_code == 200
    assert listing.json()["benchmarks"][0]["id"] == "pilot-v1"
    response = api_client.get("/api/ai-lab/benchmarks/pilot-v1")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset"]["split"] == "development"
    assert data["dataset"]["total"] == 12
    assert len(data["bands"]) == 4
    assert data["runs"][0]["label"] == "Baseline · mediana"
    assert data["bands"][0]["compared"] == 3
    assert len(data["intersections"]["rating"]) == 12
    model = next(r for r in data["runs"] if r["id"] == "model-a")
    assert model["metrics"]["mae"] == 100
    assert model["metrics"]["rating_coverage"] == 1
    assert model["generation_attempts"] == 12
    assert data["problems"][0]["predictions"]["model-a"]["justification"] == "Synthetic justification"
    text = response.content.decode()
    assert "PRIVATE" not in text and "input_format" not in text and "source_url" not in text
    assert {p: p.read_bytes() for p in root.rglob("*.json")} == before


@pytest.mark.django_db
def test_showcase_empty_and_unknown(api_client, tmp_path, settings):
    settings.AI_LAB_RESULTS_ROOT = tmp_path
    settings.AI_LAB_USE_PRIVATE_RESULTS = True
    assert api_client.get("/api/ai-lab/benchmarks").json() == {"benchmarks": []}
    assert api_client.get("/api/ai-lab/benchmarks/unknown").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("change", ["dataset", "prompt", "missing", "path", "duplicate", "malformed"])
def test_incompatible_or_broken_artifacts_are_not_compared(api_client, showcase, change):
    root, _ = showcase
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    if change == "dataset":
        run["dataset_hash"] = "different"
    elif change == "prompt":
        run["configuration"]["prompt_hash"] = "different"
    elif change == "missing":
        path.unlink()
    elif change in ("path", "duplicate"):
        index = json.loads((root / "showcase.json").read_text(encoding="utf-8"))
        index["benchmarks"][0]["runs"] = ["../outside"] if change == "path" else ["model-a", "model-a"]
        (root / "showcase.json").write_text(json.dumps(index))
    if change in ("dataset", "prompt"):
        path.write_text(json.dumps(run))
    if change == "malformed":
        path.write_text("{}")
    response = api_client.get("/api/ai-lab/benchmarks/pilot-v1")
    assert response.status_code == 503
    assert str(root) not in response.content.decode()


def test_completed_run_preserves_operational_failures_from_provenance(showcase):
    import hashlib
    from api.ai_lab.results import read_benchmark
    from api.ai_lab.runner import save_json

    root, _ = showcase
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    key = next(iter(run["predictions"]))
    original = {**run, "request_count": 2, "predictions": {key: {
        "rating_status": "transport_error", "tags_status": "transport_error",
        "responded": False, "error": "authentication", "attempts": 2,
    }}}
    original_path = root / "runs/original/run.json"
    save_json(original_path, original)
    run["request_count"] = 10
    run["provenance"] = {"original_run": "original", "original_run_sha256": hashlib.sha256(original_path.read_bytes()).hexdigest()}
    save_json(path, run)
    data = read_benchmark(root, "pilot-v1")
    model = next(r for r in data["runs"] if r["id"] == "model-a")
    assert model["generation_attempts"] == 12
    assert model["historical_failures"] == {"authentication": 1}
    assert model["metrics"]["rating_failure_rate"] == 0


def test_snapshot_is_deterministic_allowlisted_and_does_not_overwrite(showcase, tmp_path):
    from api.ai_lab.results import export_snapshot, read_benchmark, read_snapshot, list_snapshots
    root, _ = showcase
    output = tmp_path / "published" / "pilot-v1.json"
    export_snapshot(root, "pilot-v1", output)
    before = output.read_bytes()
    second = tmp_path / "copy.json"
    export_snapshot(root, "pilot-v1", second)
    assert second.read_bytes() == before
    assert "PRIVATE" not in before.decode() and "Synthetic justification" not in before.decode()
    assert json.loads(before)["schema_version"] == 1
    data = read_snapshot(output.parent, "pilot-v1")
    assert data["bands"] == read_benchmark(root, "pilot-v1")["bands"]
    assert data["runs"][1]["metrics"]["mae"] == 100
    assert list_snapshots(output.parent)[0]["id"] == "pilot-v1"
    with pytest.raises(FileExistsError):
        export_snapshot(root, "pilot-v1", output)
    assert output.read_bytes() == before


@pytest.mark.django_db
def test_published_api_needs_no_private_dataset(api_client, showcase, tmp_path, settings):
    from api.ai_lab.results import export_snapshot
    root, _ = showcase
    published = tmp_path / "published"
    export_snapshot(root, "pilot-v1", published / "pilot-v1.json")
    settings.AI_LAB_RESULTS_ROOT = tmp_path / "no-private-files"
    settings.AI_LAB_USE_PRIVATE_RESULTS = False
    settings.AI_LAB_PUBLISHED_ROOT = published
    assert api_client.get("/api/ai-lab/benchmarks").json()["benchmarks"][0]["id"] == "pilot-v1"
    assert api_client.get("/api/ai-lab/benchmarks/pilot-v1").json()["dataset"]["total"] == 12


def test_invalid_or_tampered_snapshot_is_rejected(tmp_path):
    from api.ai_lab.results import read_snapshot
    (tmp_path / "bad.json").write_text('{"schema_version": 99}')
    with pytest.raises(ValueError):
        read_snapshot(tmp_path, "bad")


def test_recovered_attempt_remains_in_operational_history(showcase):
    from api.ai_lab.results import read_benchmark
    root, _ = showcase
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    key = next(iter(run["predictions"]))
    run["attempt_history"] = {key: [{"error": "timeout"}, {"rating_status": "valid"}]}
    path.write_text(json.dumps(run), encoding="utf-8")
    model = next(r for r in read_benchmark(root, "pilot-v1")["runs"] if r["id"] == "model-a")
    assert model["historical_failures"] == {"timeout": 1}


def test_operational_history_counts_each_recorded_failed_attempt(showcase):
    from api.ai_lab.results import read_benchmark
    root, _ = showcase
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    key = next(iter(run["predictions"]))
    run["attempt_history"] = {key: [{"error": "timeout"}, {"error": "timeout"}]}
    path.write_text(json.dumps(run), encoding="utf-8")
    model = next(r for r in read_benchmark(root, "pilot-v1")["runs"] if r["id"] == "model-a")
    assert model["historical_failures"] == {"timeout": 2}


def test_presentation_metadata_and_paired_resources_are_sanitized(showcase, tmp_path):
    from api.ai_lab.results import export_snapshot, read_snapshot
    from api.ai_lab.runner import save_json
    root, manifest = showcase
    index = json.loads((root / "showcase.json").read_text())
    index["benchmarks"][0].update(description="Mesmo prompt, níveis diferentes", conclusion="Ganho modesto", run_labels={"model-a": "High"})
    save_json(root / "showcase.json", index)
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text())
    run["configuration"].update(generation={"thinking_level": "high", "private": "PRIVATE"}, timeout_seconds=90)
    for prediction in run["predictions"].values():
        prediction["raw"]["_usage"] = {"total_tokens": 30, "thinking_tokens": 20, "secret": 999}
    key = manifest["items"][0]["key"]
    run["predictions"][key].update(rating=None, rating_status="transport_error", responded=False)
    save_json(path, run)
    output = tmp_path / "public/pilot-v1.json"
    export_snapshot(root, "pilot-v1", output)
    data = read_snapshot(output.parent, "pilot-v1")
    model = data["runs"][1]
    assert data["description"] == "Mesmo prompt, níveis diferentes"
    assert data["conclusion"] == "Ganho modesto"
    assert model["label"] == "High"
    assert model["parameters"] == {"thinking_level": "high", "timeout_seconds": 90}
    assert model["token_usage"] == {"total_tokens": 330, "thinking_tokens": 220, "items_with_usage": 11, "compared_items": 11}
    assert "PRIVATE" not in output.read_text() and '"secret"' not in output.read_text()


def test_fewshot_publishes_only_reviewed_metadata_not_examples(showcase, tmp_path, monkeypatch):
    from api.ai_lab import results
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.runner import save_json
    root, _ = showcase
    text = "PRIVATE-EXAMPLES"
    monkeypatch.setattr(results, "PRIVATE_PROMPTS", {"classification_v3": {"label": "C · Exemplos", "description": "Quatro exemplos revisados.", "hash": content_hash(text)}})
    path = root / "runs/model-a/run.json"
    run = json.loads(path.read_text())
    run["configuration"].update(prompt_version="classification_v3", prompt=text, prompt_hash=content_hash(text))
    save_json(path, run)
    index = json.loads((root / "showcase.json").read_text())
    index["benchmarks"][0]["publish_prompts"] = True
    save_json(root / "showcase.json", index)
    output = tmp_path / "public/pilot-v1.json"
    results.export_snapshot(root, "pilot-v1", output)
    prompt = results.read_snapshot(output.parent, "pilot-v1")["prompts"][0]
    assert prompt["private_examples"] is True and "text" not in prompt
    assert prompt["hash"] == content_hash(text)
    assert "PRIVATE-EXAMPLES" not in output.read_text()
