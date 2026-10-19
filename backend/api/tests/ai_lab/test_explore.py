from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("model,provider", [("gemini-3.5-flash-lite", "gemini"),
    ("openai/gpt-oss-120b", "groq"), ("openai/gpt-oss-20b", "groq")])
def test_explore_uses_shared_prompt_and_selected_adapter(model, provider, explore_statement, monkeypatch):
    from api.ai_lab import explore
    adapter = Mock(return_value={"rating": 1200, "tags": [" Math "], "justification": "Short explanation"})
    resolve = Mock(return_value=adapter)
    monkeypatch.setattr(explore, "get_generator", resolve)
    result = explore.classify_problem(explore_statement, model_name=model)
    resolve.assert_called_once_with(provider, model)
    prepared, prompt, selected = adapter.call_args.args
    assert selected == model and "Taxonomia:" in prompt
    assert set(prepared) == {"description", "input_format", "output_format", "constraints", "testcases"}
    assert prepared["testcases"] == [{"input": "1 2", "output": "3"}]
    assert result["predicted_rating"] == 1200 and result["predicted_tags"] == ["math"]
    assert result["model"] == model


def test_explore_rejects_unknown_model_before_generation(explore_statement, monkeypatch):
    from api.ai_lab import explore
    generate = Mock()
    monkeypatch.setattr(explore, "get_generator", generate)
    with pytest.raises(ValueError):
        explore.classify_problem(explore_statement, model_name="paid-or-unknown")
    generate.assert_not_called()


@pytest.mark.parametrize("raw,rating,tags,discarded", [
    ({"rating": 2500, "tags": ["math"]}, 2500, ["math"], 0),
    ({"rating": 850, "tags": ["math"]}, None, ["math"], 0),
    ({"rating": 1200, "tags": ["sorting"]}, 1200, [], 1),
    ({"rating": 1200, "tags": ["math", "sorting", " DP "]}, 1200, ["dp", "math"], 1),
])
def test_explore_returns_independent_valid_parts_without_retry(raw, rating, tags, discarded, explore_statement, monkeypatch):
    from api.ai_lab import explore
    from api.ai_lab.contracts import validate_prediction
    from api.ai_lab.product import validate_product_prediction
    adapter = Mock(return_value=raw)
    monkeypatch.setattr(explore, "get_generator", lambda *args: adapter)
    result = explore.classify_problem(explore_statement)
    assert result["predicted_rating"] == rating
    assert result["predicted_tags"] == tags
    assert result["discarded_tags_count"] == discarded
    assert result["rating_status"] == validate_product_prediction(raw)["rating_status"]
    assert result["tags_status"] == validate_prediction(raw)["tags_status"]
    if discarded:
        assert validate_prediction(raw)["tags"] is None  # Benchmark contract stays strict.
    adapter.assert_called_once()


def test_explore_propagates_quota_without_retry(explore_statement, monkeypatch):
    from api.ai_lab import explore
    from api.ai_lab.contracts import ProviderFailure
    adapter = Mock(side_effect=ProviderFailure("rate_limit"))
    monkeypatch.setattr(explore, "get_generator", lambda *args: adapter)
    with pytest.raises(ProviderFailure, match="rate_limit"):
        explore.classify_problem(explore_statement)
    adapter.assert_called_once()


@pytest.mark.django_db
def test_explore_never_reuses_or_writes_product_cache(api_client, sample_problem, explore_statement, monkeypatch):
    from api import api as routes
    from api.ai_lab.classification import load_prompt
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.product import PRODUCT_PROMPT_VERSION, PRODUCT_RATING_DOMAIN
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    classify = Mock(return_value={"predicted_rating": 1200, "predicted_tags": ["math"], "reasoning": "Synthetic"})
    monkeypatch.setattr(routes, "classify_problem", classify)
    sample_problem.platform_metadata = {"ai_rating": 900, "ai_tags": ["math"], "ai_reasoning": "Legacy",
        "ai_model": "gemini-3.5-flash-lite", "ai_prompt_hash": content_hash(load_prompt(PRODUCT_PROMPT_VERSION)),
        "ai_prompt_version": PRODUCT_PROMPT_VERSION, "ai_rating_domain": PRODUCT_RATING_DOMAIN, "ai_visual_status": "not_applicable",
        "ai_lab_predictions": {"openai/gpt-oss-20b": {"rating": 900}}}
    sample_problem.save()
    original = dict(sample_problem.platform_metadata)
    url = f"/api/ai-lab/problems/{sample_problem.id}/classify"
    for model in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
        response = api_client.post(url + f"?model_name={model}")
        assert response.status_code == 200
        assert response.json()["model"] == model
        assert response.json()["cached"] is False
    response = api_client.post(url + "?model_name=openai/gpt-oss-120b")
    assert response.status_code == 200 and response.json()["cached"] is False
    assert classify.call_count == 3
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == original
    # Product still reads its original saved prediction.
    assert api_client.post(f"/api/problems/{sample_problem.id}/predict").json()["rating"] == 900


@pytest.mark.django_db
def test_prediction_rejects_unknown_model_without_scraping(api_client, sample_problem, monkeypatch):
    scraper = Mock()
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", scraper)
    response = api_client.post(f"/api/ai-lab/problems/{sample_problem.id}/classify?model_name=unknown")
    assert response.status_code == 400
    scraper.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("category,status", [("rate_limit", 429), ("authentication", 503), ("invalid_output", 502)])
def test_prediction_errors_are_safe_and_not_cached(category, status, api_client, sample_problem, explore_statement, monkeypatch):
    from api.ai_lab.contracts import ProviderFailure
    from api import api as routes
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    classify = Mock(side_effect=ProviderFailure(category))
    monkeypatch.setattr(routes, "classify_problem", classify)
    response = api_client.post(f"/api/ai-lab/problems/{sample_problem.id}/classify?model_name=openai/gpt-oss-20b")
    assert response.status_code == status
    assert response.json()["detail"]
    sample_problem.refresh_from_db()
    assert "ai_lab_predictions" not in sample_problem.platform_metadata
    classify.assert_called_once()


@pytest.mark.django_db
def test_explore_requires_authentication_and_never_classifies_on_get(client, api_client, sample_problem, monkeypatch):
    from django.test import Client
    from api import api as routes
    classify = Mock()
    monkeypatch.setattr(routes, "classify_problem", classify)
    url = f"/api/ai-lab/problems/{sample_problem.id}/classify"
    assert Client().post(url).status_code == 401
    assert api_client.get(url).status_code == 405
    classify.assert_not_called()


@pytest.mark.django_db
def test_explore_error_exposes_safe_provider_status(api_client, sample_problem, explore_statement, monkeypatch):
    from api import api as routes
    from api.ai_lab.contracts import ProviderFailure
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    monkeypatch.setattr(routes, "classify_problem", Mock(side_effect=ProviderFailure("provider_error", http_status=400)))
    response = api_client.post(f"/api/ai-lab/problems/{sample_problem.pk}/classify")
    assert response.status_code == 503
    assert "HTTP 400" in response.json()["detail"]
    assert "provider_error" in response.json()["detail"]


@pytest.mark.django_db
@pytest.mark.parametrize("raw,rating,tags,rating_status,tags_status", [
    ({"rating": 1200, "tags": ["math", "sorting"]}, 1200, ["math"], "valid", "invalid_output"),
    ({"rating": 3600, "tags": ["math"]}, None, ["math"], "out_of_domain", "valid"),
])
def test_explore_api_exposes_partial_states_without_product_writes(raw, rating, tags, rating_status, tags_status,
        api_client, sample_problem, explore_statement, monkeypatch):
    from api.ai_lab import explore
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    adapter = Mock(return_value=raw)
    monkeypatch.setattr(explore, "get_generator", lambda *args: adapter)
    original = dict(sample_problem.platform_metadata)
    response = api_client.post(f"/api/ai-lab/problems/{sample_problem.pk}/classify?model_name=openai/gpt-oss-20b")
    assert response.status_code == 200
    result = response.json()
    assert (result["rating"], result["tags"], result["rating_status"], result["tags_status"]) == (rating, tags, rating_status, tags_status)
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == original
    adapter.assert_called_once()
