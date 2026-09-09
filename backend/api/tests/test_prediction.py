from unittest.mock import patch, MagicMock
import pytest
from api.models import User, Problem, Contest


@pytest.fixture
def prediction_user(db):
    return User.objects.create_user(username="testuser", password="password123", cf_handle="testuser")


@pytest.fixture
def prediction_api_client(client, prediction_user):
    from ninja_jwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(prediction_user)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {refresh.access_token}'
    return client


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
def test_predict_problem_success(mock_classify, mock_scraper_class, prediction_api_client, setup_problem):
    """
    Cenário: O problema ainda não possui os dados preditivos no banco de dados.
    Resultado Esperado: A API deve chamar o scraper, submeter à IA, gravar os dados
    (rating, tags, reasoning) em platform_metadata e retornar status 200 com os dados.
    """
    mock_scraper = MagicMock()
    mock_scraper_class.return_value = mock_scraper
    mock_scraper.scrape.return_value = {"title": "Test", "description": "Desc"}
    
    mock_classify.return_value = {
        "predicted_rating": 1500,
        "predicted_tags": ["math", "greedy"],
        "reasoning": "Test reasoning"
    }
    
    response = prediction_api_client.post(f"/api/problems/{setup_problem.id}/predict")
    
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 1500
    assert data["tags"] == ["math", "greedy"]
    assert data["reasoning"] == "Test reasoning"
    
    setup_problem.refresh_from_db()
    assert setup_problem.platform_metadata["ai_rating"] == 1500
    assert setup_problem.platform_metadata["ai_tags"] == ["math", "greedy"]
    assert setup_problem.platform_metadata["ai_reasoning"] == "Test reasoning"


@pytest.mark.django_db
@patch('api.services.scrapers.CodeforcesScraper')
@patch('api.api.classify_problem')
def test_predict_problem_cached(mock_classify, mock_scraper_class, prediction_api_client, setup_problem):
    """
    Cenário: O problema já possui os dados de predição em platform_metadata.
    Resultado Esperado: A API deve retornar os dados em cache imediatamente.
    """
    setup_problem.platform_metadata = {
        "ai_rating": 1200,
        "ai_tags": ["implementation"],
        "ai_reasoning": "Already classified"
    }
    setup_problem.save()
    
    response = prediction_api_client.post(f"/api/problems/{setup_problem.id}/predict")
    
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == 1200
    assert data["tags"] == ["implementation"]
    assert data["reasoning"] == "Already classified"
    
    mock_scraper_class.assert_not_called()
    mock_classify.assert_not_called()
