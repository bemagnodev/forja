from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("platform", ["atcoder", "cses"])
def test_live_scrapers_keep_image_markers_without_requesting_image_bytes(platform, monkeypatch):
    from api.services.scrapers.atcoder import AtCoderScraper
    from api.services.scrapers.cses import CSESScraper
    if platform == "atcoder":
        html = '<div id="task-statement"><span class="lang-en">' + ''.join(
            f'<section><h3>{title}</h3><p>{content}</p></section>' for title, content in (
                ("Problem Statement", 'Text before <img src="/diagram.png" alt="Graph"> after'),
                ("Input", "Two integers"), ("Output", "One integer"))) + '</span></div>'
        scraper = AtCoderScraper()
    else:
        html = '<div class="content"><p>Before <img src="/diagram.png" alt="Graph"> after</p><h1 id="input">Input</h1><p>Two integers</p><h1 id="output">Output</h1><p>One integer</p></div>'
        scraper = CSESScraper()
    response = Mock(content=html.encode())
    get = Mock(return_value=response)
    monkeypatch.setattr(f"api.services.scrapers.{platform}.requests.get", get)
    value = scraper.scrape("https://example.invalid/task/1")
    assert "[image:1]" in value["description"]
    assert value["images"] == [{"url": "https://example.invalid/diagram.png", "alt": "Graph", "position": 1}]
    get.assert_called_once_with("https://example.invalid/task/1", timeout=10)


def test_codeforces_payload_is_identical_for_dataset_and_live(statement_html, monkeypatch):
    from api.services.scrapers.codeforces import CodeforcesScraper
    from api.ai_lab.dataset import parse_statement, prepare_input
    from api.ai_lab import explore
    response = Mock(text=statement_html)
    monkeypatch.setattr("api.services.scrapers.codeforces.requests.get", lambda *a, **k: response)
    statement = CodeforcesScraper().scrape("https://codeforces.com/contest/1/problem/A")
    adapter = Mock(return_value={"rating": 1200, "tags": ["math"]})
    monkeypatch.setattr(explore, "get_generator", lambda *a: adapter)
    explore.classify_problem(statement)
    assert adapter.call_args.args[0] == prepare_input(parse_statement(statement_html))
    assert r"\unknown{x}" in statement["description"]


def test_shared_parser_preserves_image_position_and_marks_unprocessed(statement_html, monkeypatch):
    from api.services.scrapers.codeforces import CodeforcesScraper
    from api.ai_lab import explore
    html = statement_html.replace("Compute", 'Before<img src="/diagram.png" alt="Graph">After Compute')
    statement = CodeforcesScraper.parse_html(html, "https://codeforces.com/contest/1/problem/A")
    assert statement["images"][0]["url"] == "https://codeforces.com/diagram.png"
    assert statement["images"][0]["alt"] == "Graph"
    assert "[image:1]" in statement["description"]
    adapter = Mock(return_value={"rating": 1200, "tags": ["math"]})
    monkeypatch.setattr(explore, "get_generator", lambda *a: adapter)
    result = explore.classify_problem(statement)
    assert result["visual_status"] == "unprocessed"
    assert "imagem" in result["reasoning"].lower()


def test_parser_collects_multiple_description_blocks(statement_html):
    from api.services.scrapers.codeforces import CodeforcesScraper
    html = statement_html.replace('<div class="input-specification">', '<p>Extra restriction n &lt; 50</p><div class="input-specification">')
    assert "Extra restriction" in CodeforcesScraper.parse_html(html)["description"]


@pytest.mark.django_db
def test_visual_result_is_explicit_in_explore_and_saved_with_product_warning(api_client, sample_problem, monkeypatch):
    from api import api as routes
    sample_problem.platform_metadata = {"ai_rating": 900, "ai_tags": ["math"], "ai_reasoning": "Previous"}
    sample_problem.save()
    monkeypatch.setattr(routes, "_classify_for_ui", lambda *a: ({"predicted_rating": 1200,
        "predicted_tags": ["math"], "reasoning": "Avaliação parcial: imagem não processada",
        "rating_status": "valid", "tags_status": "valid", "visual_status": "unprocessed"}, {}))
    response = api_client.post(f"/api/ai-lab/problems/{sample_problem.id}/classify")
    assert response.status_code == 200
    assert response.json()["visual_status"] == "unprocessed"
    response = api_client.post(f"/api/problems/{sample_problem.id}/predict?force=true")
    assert response.status_code == 200
    sample_problem.refresh_from_db()
    assert sample_problem.platform_metadata["ai_rating"] == 1200
    assert sample_problem.platform_metadata["ai_visual_status"] == "unprocessed"


def test_text_benchmark_cannot_freeze_unprocessed_visual_input(statement_html):
    from api.services.scrapers.codeforces import CodeforcesScraper
    from api.ai_lab.dataset import prepare_input, require_reviewed
    statement = CodeforcesScraper.parse_html(statement_html.replace("Compute", '<img src="/graph.png">Compute'))
    with pytest.raises(ValueError, match="multimodal"):
        require_reviewed({"input": prepare_input(statement), "review": {}})
