import pytest
from ninja.testing import TestClient
from api.models import Problem, Contest
from api.api import api
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="module")
def test_client():
    return TestClient(api)

@pytest.fixture
def setup_problem(db):
    contest = Contest.objects.create(name="Test Contest", platform="CF_OFFICIAL", platform_id="123")
    return Problem.objects.create(
        title="Test Problem",
        platform="CF_OFFICIAL",
        platform_id="123A",
        contest=contest,
        platform_metadata={}
    )

@pytest.mark.django_db
@patch('api.services.scrapers.CodeforcesScraper')
@patch('api.api.classify_problem')
def test_predict_problem_success(mock_classify, mock_scraper_class, test_client, setup_problem):
    """
    Cenário: O problema ainda não possui os dados preditivos no banco de dados.
    Resultado Esperado: A API deve chamar o scraper, submeter à IA, gravar os dados
    (rating, tags, reasoning) em platform_metadata e retornar status 200 com os dados.
    """
    # Setup mocks
    mock_scraper = MagicMock()
    mock_scraper_class.return_value = mock_scraper
    mock_scraper.scrape.return_value = {"title": "Test", "description": "Desc"}
    
    mock_classify.return_value = {
        "predicted_rating": 1500,
        "predicted_tags": ["math", "greedy"],
        "reasoning": "Test reasoning"
    }
    
    # Send request
    response = test_client.post(f"/problems/{setup_problem.id}/predict")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 1500
    assert data["tags"] == ["math", "greedy"]
    assert data["reasoning"] == "Test reasoning"
    
    # Verify DB updated
    setup_problem.refresh_from_db()
    assert setup_problem.platform_metadata["ai_rating"] == 1500
    assert setup_problem.platform_metadata["ai_tags"] == ["math", "greedy"]
    assert setup_problem.platform_metadata["ai_reasoning"] == "Test reasoning"

@pytest.mark.django_db
@patch('api.services.scrapers.CodeforcesScraper')
@patch('api.api.classify_problem')
def test_predict_problem_cached(mock_classify, mock_scraper_class, test_client, setup_problem):
    """
    Cenário: O problema já possui os dados de predição em platform_metadata.
    Resultado Esperado: A API deve retornar os dados em cache imediatamente.
    """
    # Pre-populate metadata
    setup_problem.platform_metadata = {
        "ai_rating": 1200,
        "ai_tags": ["implementation"],
        "ai_reasoning": "Already classified"
    }
    setup_problem.save()
    
    # Send request
    response = test_client.post(f"/problems/{setup_problem.id}/predict")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 1200
    assert data["tags"] == ["implementation"]
    assert data["reasoning"] == "Already classified"
    
    # Verify no scraper/ai was called
    mock_scraper_class.assert_not_called()
    mock_classify.assert_not_called()
