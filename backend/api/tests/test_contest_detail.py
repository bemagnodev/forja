import pytest
from api.models import Contest, ContestParticipation, Problem, User, UserProblemTracking


@pytest.mark.django_db
def test_detail_requires_own_participation(api_client, client, base_user):
    # Arrange
    contest = Contest.objects.create(platform='CF_GYM', platform_id='106687', name='Treino')
    other = User.objects.create(username='other')
    ContestParticipation.objects.create(user=other, contest=contest)
    # Act / Assert
    assert api_client.get(f'/api/contests/{contest.id}').status_code == 404
    assert api_client.get('/api/contests/99999').status_code == 404
    client.defaults.pop('HTTP_AUTHORIZATION', None)
    assert client.get(f'/api/contests/{contest.id}').status_code == 401


@pytest.mark.django_db
def test_detail_and_list_share_live_progress(api_client, base_user):
    # Arrange
    contest = Contest.objects.create(platform='CF_GYM', platform_id='106687', name='Treino')
    ContestParticipation.objects.create(user=base_user, contest=contest)
    problem = Problem.objects.create(platform='CF_GYM', platform_id='106687F', title='F', contest=contest)
    Problem.objects.create(platform='CF_GYM', platform_id='106687G', title='G', contest=contest)
    tracker = UserProblemTracking.objects.create(user=base_user, problem=problem, system_status='UNATTEMPTED')
    # Act
    response = api_client.get(f'/api/contests/{contest.id}')
    # Assert: catalogue problems without a tracking still count as unattempted.
    assert response.status_code == 200
    assert response.json()['contest_name'] == 'Treino'
    assert response.json()['url'] == 'https://codeforces.com/gym/106687'
    assert response.json()['progress']['total'] == 2
    assert response.json()['progress']['unattempted'] == 2
    tracker.review_status = 'DONE'
    tracker.save()
    detail = api_client.get(f'/api/contests/{contest.id}').json()
    listing = api_client.get('/api/contests').json()[0]
    assert detail['progress'] == listing['progress']
    assert detail['progress']['upsolved'] == 1
    assert detail['progress']['total'] == 2
