from pathlib import Path

import pytest


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
