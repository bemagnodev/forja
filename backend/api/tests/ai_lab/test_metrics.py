import pytest


def test_rating_bands_use_official_rating_and_paired_intersection():
    from api.ai_lab.metrics import compare_by_band
    refs = {key: {"rating": rating, "tags": ["math"]} for key, rating in
            (("a", 800), ("b", 1100), ("c", 1200), ("d", 1500), ("e", 1900), ("f", 2400))}
    runs = {"one": {k: {"rating": ref["rating"] + 100, "rating_status": "valid"} for k, ref in refs.items()},
            "two": {"a": {"rating": 2400, "rating_status": "valid"},
                    "c": {"rating": 1200, "rating_status": "valid"}}}
    bands = compare_by_band(refs, runs)
    assert [b["label"] for b in bands] == ["800–1100", "1200–1500", "1600–1900", "2000–2400"]
    assert bands[0]["total"] == 2 and bands[0]["compared"] == 1
    assert bands[0]["mae"] == {"one": 100, "two": 1600}
    assert bands[1]["mae"]["two"] == 0
    assert bands[2]["compared"] == 0 and bands[2]["mae"]["one"] is None
    assert bands[3]["total"] == 1


def test_metrics_use_same_valid_intersection_and_show_coverage():
    from api.ai_lab.metrics import compare_runs

    references = {"a": {"rating": 1000, "tags": ["math"]}, "b": {"rating": 1400, "tags": ["dp"]}, "c": {"rating": 1800, "tags": ["graphs"]}}
    runs = {"one": {
        "a": {"rating": 1200, "tags": ["math"], "rating_status": "valid", "tags_status": "valid", "responded": True, "duration": 2},
        "b": {"rating": None, "tags": None, "rating_status": "out_of_domain", "tags_status": "invalid_output", "responded": True, "duration": 4},
    }, "two": {
        "a": {"rating": 900, "tags": ["math", "dp"], "rating_status": "valid", "tags_status": "valid", "responded": True, "duration": 1},
        "b": {"rating": 1400, "tags": ["dp"], "rating_status": "valid", "tags_status": "valid", "responded": True, "duration": 3},
        "c": {"rating_status": "transport_error", "tags_status": "transport_error", "responded": False},
    }}
    report = compare_runs(references, runs)
    assert report["rating_intersection"] == ["a"]
    assert report["tags_intersection"] == ["a"]
    one, two = report["runs"]["one"], report["runs"]["two"]
    assert one["mae"] == 200 and one["within_200"] == 1
    assert two["mae"] == 100 and two["tags_micro_f1"] == pytest.approx(2 / 3)
    assert one["rating_coverage"] == pytest.approx(1 / 3)
    assert one["pending"] == 1 and one["responded"] == 2
    assert one["rating_failure_rate"] == pytest.approx(1 / 3)
    assert two["rating_failure_rate"] == pytest.approx(1 / 3)
    assert one["latency_median"] == 3


def test_empty_intersection_is_unavailable_not_zero():
    from api.ai_lab.metrics import compare_runs

    report = compare_runs({"a": {"rating": 800, "tags": ["math"]}}, {"one": {}, "two": {}})
    assert report["runs"]["one"]["mae"] is None
    assert report["runs"]["one"]["tags_micro_f1"] is None


def test_baseline_does_not_remove_tag_metrics_for_models():
    from api.ai_lab.metrics import compare_runs

    references = {"a": {"rating": 1000, "tags": ["math"]}}
    runs = {"baseline": {"a": {"rating": 1100, "rating_status": "valid", "tags_status": "not_applicable", "responded": True}},
            "model": {"a": {"rating": 1000, "rating_status": "valid", "tags": ["math"], "tags_status": "valid", "responded": True}}}
    result = compare_runs(references, runs)
    assert result["runs"]["model"]["tags_micro_f1"] == 1
    assert result["runs"]["baseline"]["tags_micro_f1"] is None
    assert result["runs"]["baseline"]["tags_failure_rate"] is None


def test_baseline_fitted_on_development_not_final(catalog, statement_html):
    from api.ai_lab.dataset import build_manifest, record_review, freeze_manifest
    from api.ai_lab.classification import baseline_predictions

    development = build_manifest(catalog, lambda url: statement_html)
    for item in development["items"]:
        record_review(item, "mentor", "2026-10-17")
    freeze_manifest(development)
    final = build_manifest(catalog, lambda url: statement_html, split="final", development=development)
    for item in final["items"]:
        record_review(item, "mentor", "2026-10-17")
    freeze_manifest(final)
    predictions = baseline_predictions(final, development)
    assert len(predictions) == 60
    assert {p["rating"] for p in predictions.values()} == {1400}
