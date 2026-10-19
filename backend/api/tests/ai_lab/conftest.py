from pathlib import Path

import pytest


@pytest.fixture
def few_shot_context(catalog, statement_html, reviewed_manifest, tmp_path):
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest
    from api.ai_lab.runner import save_json
    development = reviewed_manifest()
    evaluation = build_manifest(catalog, lambda url: statement_html, "final", 42, development)
    for item in evaluation["items"]:
        record_review(item, "synthetic reviewer", "2026-10-18")
    freeze_manifest(evaluation)
    selected = []
    for lo, hi in ((800, 1100), (1200, 1500), (1600, 1900), (2000, 2400)):
        item = next(i for i in development["items"] if lo <= i["reference"]["rating"] <= hi)
        selected.append({"key": item["key"], "input": item["input"],
                         "output": {**item["reference"], "justification": "Synthetic reviewed explanation"}})
    artifact = {"schema_version": 1, "development_hash": development["hash"], "examples": selected}
    path = tmp_path / "examples.json"
    save_json(path, artifact)
    return development, evaluation, path, artifact


@pytest.fixture
def explore_statement():
    return {"description": "Synthetic statement", "input_format": "Two integers",
            "output_format": "One integer", "constraints": "n <= 10",
            "testcases": [{"input": "1 2", "output": "3", "private": "hidden"}],
            "title": "secret-id", "rating": 1200, "tags": ["math"], "total_solved": 42}


@pytest.fixture
def statement_html():
    return (Path(__file__).parent / "fixtures/codeforces/statement.html").read_text(encoding="utf-8")


@pytest.fixture
def catalog():
    return {"problems": [
        {"contestId": 1000 + band * 100 + i, "index": "A", "rating": rating,
         "tags": ["math"], "type": "PROGRAMMING"}
        for band, rating in enumerate((800, 1200, 1600, 2000)) for i in range(24)
    ]}


@pytest.fixture
def mock_collection(catalog, statement_html, tmp_path, monkeypatch):
    from api.management.commands import prepare_ai_dataset as command

    monkeypatch.setattr(command, "guarded_root", lambda options: tmp_path)
    monkeypatch.setattr(command, "fetch_catalog", lambda: catalog)
    monkeypatch.setattr(command, "fetch_html", lambda url: statement_html)
    return tmp_path


@pytest.fixture
def reviewed_manifest(catalog, statement_html):
    def make(version="cf-rating-v1"):
        from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest

        manifest = build_manifest(catalog, lambda url: statement_html, version=version)
        for item in manifest["items"]:
            record_review(item, "mentor", "2026-10-17")
        freeze_manifest(manifest)
        return manifest
    return make
