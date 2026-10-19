from unittest.mock import Mock

import pytest
from django.core.management import call_command


@pytest.mark.django_db
@pytest.mark.parametrize("provenance", [{}, {"ai_model": "openai/gpt-oss-20b", "ai_prompt_hash": "old"},
                                       {"ai_model": "gemini-3.5-flash-lite", "ai_prompt_hash": "old"}])
def test_product_does_not_reuse_predictions_from_unknown_model_or_prompt(provenance,
        api_client, sample_problem, explore_statement, monkeypatch):
    from api import api as routes
    sample_problem.platform_metadata = {"ai_rating": 900, "ai_tags": ["math"], "ai_reasoning": "Old", **provenance}
    sample_problem.save()
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    classify = Mock(return_value={"predicted_rating": 1200, "predicted_tags": ["math"], "reasoning": "Current"})
    monkeypatch.setattr(routes, "classify_problem", classify)
    response = api_client.post(f"/api/problems/{sample_problem.pk}/predict")
    assert response.status_code == 200 and response.json()["rating"] == 1200
    classify.assert_called_once_with(explore_statement, model_name="gemini-3.5-flash-lite")
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata["ai_prompt_version"] == "product_classification_v1"


@pytest.mark.django_db
@pytest.mark.parametrize("platform", ["CF_OFFICIAL", "ATCODER", "CSES"])
@pytest.mark.parametrize("route", ["problems/{id}/predict", "ai-lab/problems/{id}/classify"])
def test_live_routes_default_to_benchmark_winner_and_exact_product_prompt(platform, route,
        api_client, sample_problem, explore_statement, monkeypatch):
    from api.ai_lab import explore
    from api.ai_lab.classification import load_prompt
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.product import PRODUCT_PROMPT_VERSION
    sample_problem.platform = platform
    sample_problem.save()
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    for cls in ("CodeforcesScraper", "AtCoderScraper", "CSESScraper"):
        monkeypatch.setattr("api.services.scrapers." + cls, lambda: scraper)
    generator = Mock(return_value={"rating": 1200, "tags": ["math"], "justification": "Synthetic"})
    resolve = Mock(return_value=generator)
    monkeypatch.setattr(explore, "get_generator", resolve)
    original = dict(sample_problem.platform_metadata)
    response = api_client.post("/api/" + route.format(id=sample_problem.pk))
    assert response.status_code == 200
    resolve.assert_called_once_with("gemini", "gemini-3.5-flash-lite")
    assert generator.call_args.args[1:] == (load_prompt(PRODUCT_PROMPT_VERSION), "gemini-3.5-flash-lite")
    assert response.json()["prompt_hash"] == content_hash(load_prompt(PRODUCT_PROMPT_VERSION))
    sample_problem.refresh_from_db()
    if route.startswith("ai-lab/"):
        assert sample_problem.platform_metadata == original
        assert api_client.post("/api/" + route.format(id=sample_problem.pk)).json()["cached"] is False
        assert generator.call_count == 2
    else:
        assert sample_problem.platform_metadata["ai_model"] == "gemini-3.5-flash-lite"
        assert sample_problem.platform_metadata["ai_prompt_hash"] == response.json()["prompt_hash"]
        assert api_client.post("/api/" + route.format(id=sample_problem.pk)).json()["cached"] is True
        generator.assert_called_once()


@pytest.mark.django_db
def test_prediction_merges_after_external_call_and_preserves_other_fields(api_client, sample_problem, explore_statement, monkeypatch):
    from api import api as routes
    from api.models import Problem
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)

    def classify(*args, **kwargs):
        # Deterministic interleaving: another writer finishes during inference.
        Problem.objects.filter(pk=sample_problem.pk).update(title="Updated by sync", platform_metadata={
            "rating": 1900, "tags": ["dp"], "other_cache": {"rating": 1600}})
        return {"predicted_rating": 1200, "predicted_tags": ["math"], "reasoning": "Synthetic"}

    monkeypatch.setattr(routes, "classify_problem", classify)
    response = api_client.post(f"/api/problems/{sample_problem.pk}/predict?force=true")
    assert response.status_code == 200
    sample_problem.refresh_from_db()
    assert sample_problem.title == "Updated by sync"
    assert sample_problem.platform_metadata["rating"] == 1900
    assert sample_problem.platform_metadata["other_cache"] == {"rating": 1600}
    assert sample_problem.platform_metadata["ai_rating"] == 1200
    assert response.json()["real_rating"] == 1900


@pytest.mark.django_db
def test_atcoder_metadata_refresh_preserves_saved_classification(monkeypatch):
    from api.models import Problem
    from api.management.commands import sync_atcoder_metadata as command
    problem = Problem.objects.create(platform="ATCODER", platform_id="abc100_a", title="Before", platform_metadata={
        "rating": 800, "ai_rating": 1200, "ai_tags": ["math"], "ai_reasoning": "Saved", "other": 7})
    client = Mock()
    client.get_contests.return_value = [{"id": "abc100", "title": "ABC", "start_epoch_second": 1}]
    client.get_problems.return_value = [{"id": "abc100_a", "contest_id": "abc100", "title": "A - New"}]
    client.get_problem_difficulties.return_value = {"abc100_a": 1000}
    monkeypatch.setattr(command, "AtCoderClient", lambda **kwargs: client)
    call_command("sync_atcoder_metadata", verbosity=0)
    problem.refresh_from_db()
    assert problem.platform_metadata == {"rating": 1000, "ai_rating": 1200, "ai_tags": ["math"], "ai_reasoning": "Saved", "other": 7}


@pytest.mark.django_db
def test_metadata_upsert_merges_both_orders_without_carrying_stale_objects(sample_problem):
    from api.services.problem_metadata import upsert_problem_metadata
    key = {"platform": sample_problem.platform, "platform_id": sample_problem.platform_id}
    for first, second in (({"ai_rating": 1400}, {"rating": 1800}), ({"rating": 1900}, {"ai_tags": ["dp"]})):
        upsert_problem_metadata(**key, metadata=first)
        upsert_problem_metadata(**key, metadata=second)
        sample_problem.refresh_from_db()
        assert all(sample_problem.platform_metadata[k] == v for k, v in {**first, **second}.items())


@pytest.mark.django_db
def test_partial_prediction_does_not_replace_product_result(api_client, sample_problem, explore_statement, monkeypatch):
    from api import api as routes
    sample_problem.platform_metadata = {"ai_rating": 1600, "ai_tags": ["dp"], "ai_reasoning": "Saved"}
    sample_problem.save()
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    classify = Mock(return_value={"predicted_rating": 1200, "predicted_tags": ["math"], "reasoning": "Partial",
        "rating_status": "valid", "tags_status": "invalid_output", "discarded_tags_count": 1})
    monkeypatch.setattr(routes, "classify_problem", classify)
    response = api_client.post(f"/api/problems/{sample_problem.pk}/predict?force=true")
    assert response.status_code == 502
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == {"ai_rating": 1600, "ai_tags": ["dp"], "ai_reasoning": "Saved"}


@pytest.mark.django_db
def test_product_rejects_experimental_model_before_inference(api_client, sample_problem, monkeypatch):
    from api import api as routes
    classify = Mock()
    monkeypatch.setattr(routes, "classify_problem", classify)
    response = api_client.post(f"/api/problems/{sample_problem.pk}/predict?model_name=openai/gpt-oss-20b&force=true")
    assert response.status_code == 400
    classify.assert_not_called()
