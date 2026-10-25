from unittest.mock import Mock

import pytest


@pytest.mark.parametrize('rating,expected', [(0, True), (1200, True), (3800, True),
    (None, False), (False, False), ('1200', False), (float('nan'), False), (float('inf'), False)])
def test_native_rating_policy_is_independent_of_ai_domain(rating, expected):
    from api.ai_lab.product import has_native_rating
    assert has_native_rating(rating) is expected


@pytest.mark.django_db
@pytest.mark.parametrize('rating', [0, 1200, 3800])
@pytest.mark.parametrize('force', ['false', 'true'])
def test_native_rating_blocks_product_before_scraping_inference_or_cached_result(api_client, sample_problem,
        rating, force, monkeypatch):
    from api import api as routes
    from api.ai_lab.classification import load_prompt
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.product import PRODUCT_PROMPT_VERSION, PRODUCT_RATING_DOMAIN
    sample_problem.platform_metadata = {'rating': rating, 'ai_rating': 1500, 'ai_tags': ['math'],
        'ai_reasoning': 'Historical', 'ai_model': 'gemini-3.5-flash-lite',
        'ai_prompt_hash': content_hash(load_prompt(PRODUCT_PROMPT_VERSION)),
        'ai_prompt_version': PRODUCT_PROMPT_VERSION, 'ai_rating_domain': PRODUCT_RATING_DOMAIN,
        'ai_visual_status': 'unprocessed'}
    sample_problem.save()
    before = dict(sample_problem.platform_metadata)
    classify = Mock()
    monkeypatch.setattr(routes, '_classify_for_ui', classify)
    response = api_client.post(f'/api/problems/{sample_problem.pk}/predict?force={force}')
    assert response.status_code == 409
    assert response.json()['diagnostic']['code'] == 'native_rating_available'
    classify.assert_not_called()
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == before


@pytest.mark.django_db
def test_native_rating_remains_available_to_explore_without_writes(api_client, sample_problem,
        explore_statement, monkeypatch):
    from api import api as routes
    sample_problem.platform_metadata = {'rating': 1200}
    sample_problem.save()
    classify = Mock(return_value=({'predicted_rating': 1500, 'predicted_tags': ['math'],
                                   'reasoning': 'Synthetic'}, explore_statement))
    monkeypatch.setattr(routes, '_classify_for_ui', classify)
    response = api_client.post(f'/api/ai-lab/problems/{sample_problem.pk}/classify')
    assert response.status_code == 200
    assert response.json()['real_rating'] == 1200
    classify.assert_called_once()
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == {'rating': 1200}


@pytest.mark.django_db
def test_tags_without_native_rating_do_not_block_product(api_client, sample_problem, explore_statement, monkeypatch):
    from api import api as routes
    sample_problem.platform_metadata = {'tags': ['math']}
    sample_problem.save()
    classify = Mock(return_value=({'predicted_rating': 1500, 'predicted_tags': ['math'],
                                   'reasoning': 'Synthetic'}, explore_statement))
    monkeypatch.setattr(routes, '_classify_for_ui', classify)
    assert api_client.post(f'/api/problems/{sample_problem.pk}/predict').status_code == 200
    classify.assert_called_once()


def test_product_prompt_cannot_enter_benchmark_runner(reviewed_manifest, tmp_path):
    from api.ai_lab.runner import run_local
    from api.ai_lab.product import PRODUCT_PROMPT_VERSION
    generate = Mock(return_value={"rating": 1200, "tags": ["math"]})
    config = {"provider": "fake", "model": "fake", "execution_policy": "managed-v1",
              "prompt_version": PRODUCT_PROMPT_VERSION}
    with pytest.raises(ValueError, match="Product prompt"):
        run_local(reviewed_manifest(), config, tmp_path / "run.json", generate, max_requests=1)
    generate.assert_not_called()
    assert not (tmp_path / "run.json").exists()


@pytest.mark.parametrize("rating,status", [(800, "valid"), (2400, "valid"), (2500, "valid"),
    (3500, "valid"), (2550, "invalid_output"), (799, "out_of_domain"),
    (3600, "out_of_domain"), (True, "invalid_output"), ("2600", "invalid_output")])
def test_product_rating_domain_is_independent_of_benchmark(rating, status):
    from api.ai_lab.product import validate_product_prediction
    from api.ai_lab.contracts import validate_prediction
    raw = {"rating": rating, "tags": ["math"], "justification": "Synthetic"}
    result = validate_product_prediction(raw)
    assert result["rating_status"] == status
    assert result["rating"] == (rating if status == "valid" else None)
    assert result["raw"] == raw
    if type(rating) is int and rating >= 2500:
        assert validate_prediction(raw)["rating_status"] == "out_of_domain"


def test_product_prompt_is_versioned_without_modifying_benchmark_prompts(explore_statement, monkeypatch):
    from api.ai_lab import explore
    from api.ai_lab.classification import load_prompt
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.product import PRODUCT_PROMPT_VERSION, PRODUCT_RATING_DOMAIN
    from api.ai_lab.results import REVIEWED_PROMPTS
    generate = Mock(return_value={"rating": 3500, "tags": ["math"]})
    monkeypatch.setattr(explore, "get_generator", lambda *a: generate)
    result = explore.classify_problem(explore_statement)
    prompt = generate.call_args.args[1]
    assert "800 e 3500" in prompt and "imagens" in prompt
    assert result["prompt_version"] == PRODUCT_PROMPT_VERSION
    assert result["prompt_hash"] == content_hash(prompt)
    assert result["rating_domain"] == PRODUCT_RATING_DOMAIN
    assert result["predicted_rating"] == 3500
    for version, metadata in REVIEWED_PROMPTS.items():
        assert content_hash(load_prompt(version)) == metadata["hash"]


@pytest.mark.django_db
@pytest.mark.parametrize("changed,value", [("ai_prompt_version", "classification_v1"),
    ("ai_prompt_hash", "old"), ("ai_rating_domain", "800-2400"),
    ("ai_model", "openai/gpt-oss-20b"), ("ai_visual_status", None)])
def test_product_cache_requires_full_contract_identity(changed, value, api_client, sample_problem,
        explore_statement, monkeypatch):
    from api.ai_lab import explore
    from api.ai_lab.classification import load_prompt
    from api.ai_lab.dataset import content_hash
    from api.ai_lab.product import PRODUCT_PROMPT_VERSION, PRODUCT_RATING_DOMAIN
    sample_problem.platform_metadata = {"ai_rating": 2600, "ai_tags": ["math"], "ai_reasoning": "Old",
        "ai_model": explore.DEFAULT_MODEL, "ai_prompt_version": PRODUCT_PROMPT_VERSION,
        "ai_prompt_hash": content_hash(load_prompt(PRODUCT_PROMPT_VERSION)),
        "ai_rating_domain": PRODUCT_RATING_DOMAIN, "ai_visual_status": "not_applicable", changed: value}
    sample_problem.save()
    scraper = Mock()
    scraper.scrape.return_value = explore_statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    generator = Mock(return_value={"rating": 3500, "tags": ["math"], "justification": "New"})
    monkeypatch.setattr(explore, "get_generator", lambda *a: generator)
    response = api_client.post(f"/api/problems/{sample_problem.pk}/predict")
    assert response.status_code == 200 and response.json()["rating"] == 3500
    assert response.json()["cached"] is False
    generator.assert_called_once()
    assert api_client.post(f"/api/problems/{sample_problem.pk}/predict").json()["cached"] is True
    generator.assert_called_once()


@pytest.mark.django_db
def test_visual_product_prediction_survives_cache_queue_and_contest_without_explore_writes(
        api_client, base_user, sample_problem, explore_statement, monkeypatch):
    from api.ai_lab import explore
    from api.models import QueueItem
    statement = {**explore_statement, "description": "Text before [image:1] and after.",
        "images": [{"url": "https://example.invalid/diagram.png", "alt": "Diagram", "position": 1}]}
    scraper = Mock()
    scraper.scrape.return_value = statement
    monkeypatch.setattr("api.services.scrapers.CodeforcesScraper", lambda: scraper)
    generate = Mock(return_value={"rating": 2600, "tags": ["math"], "justification": "Synthetic text estimate"})
    monkeypatch.setattr(explore, "get_generator", lambda *a: generate)
    QueueItem.objects.create(user=base_user, linked_problem=sample_problem, title="Synthetic")
    response = api_client.post(f"/api/problems/{sample_problem.pk}/predict")
    assert response.status_code == 200
    assert response.json()["rating"] == 2600 and response.json()["visual_status"] == "unprocessed"
    payload = generate.call_args.args[0]
    assert "[image:1]" in payload["description"]
    assert "images" not in payload  # Text/markers only, no image URL or multimodal request.
    sample_problem.refresh_from_db()
    saved = dict(sample_problem.platform_metadata)
    assert saved["ai_visual_status"] == "unprocessed"
    cached = api_client.post(f"/api/problems/{sample_problem.pk}/predict").json()
    assert cached["cached"] is True and cached["visual_status"] == "unprocessed"
    for _ in range(2):
        assert api_client.get("/api/queue").json()[0]["ai_visual_status"] == "unprocessed"
        rows = api_client.get(f"/api/contests/{sample_problem.contest_id}/problems").json()
        assert rows[0]["ai_visual_status"] == "unprocessed" and rows[0]["ai_rating"] == 2600
    generate.assert_called_once()
    result = api_client.post(f"/api/ai-lab/problems/{sample_problem.pk}/classify")
    assert result.status_code == 200 and result.json()["visual_status"] == "unprocessed"
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata == saved
    assert generate.call_count == 2
