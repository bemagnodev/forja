from django.test import TestCase, Client
from django.urls import reverse
from api.models import User, Problem, Submission, Contest, ContestParticipation, UserProblemTracking

class DashboardStatsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        # Não precisamos gerar token de JWT aqui pois podemos forçar a autenticação pelo Ninja (ou simular)
        # Se usarmos JWTAuth do Ninja, um client normal não funciona a menos que passemos o token.
        # Vamos contornar buscando o token primeiro
        
        url = reverse('api:token_obtain_pair')
        resp = self.client.post(url, '{"username": "testuser", "password": "password123"}', content_type='application/json')
        self.token = resp.json()['access']
        # Set bearer token via headers in client.get


        # Setup básico de dados
        c = Contest.objects.create(platform='CF_OFFICIAL', platform_id='1000', name='Test Contest')
        p = Problem.objects.create(platform='CF_OFFICIAL', platform_id='1000A', title='Test Problem', contest=c, platform_metadata={'rating': 1200, 'tags': ['math']})
        
        # Simular tracking resolvido
        UserProblemTracking.objects.create(user=self.user, problem=p, system_status='SOLVED_LIVE', review_status='DONE')
        
        # Simular submissão AC
        from django.utils import timezone
        Submission.objects.create(
            platform_submission_id='sub1',
            user=self.user,
            problem=p,
            participant_type='CONTESTANT',
            verdict='OK',
            creation_time=timezone.now()
        )

    def test_dashboard_stats_endpoint(self):
        url = '/api/dashboard/stats'
        response = self.client.get(url, HTTP_AUTHORIZATION='Bearer ' + self.token)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('kpis', data)
        self.assertEqual(data['kpis']['total_solved'], 1)
        self.assertEqual(data['kpis']['acceptance_rate'], 100.0)
        
        self.assertIn('difficulty_breakdown', data)
        self.assertEqual(data['difficulty_breakdown'].get('1200'), 1)
        
        self.assertIn('topics', data)
        self.assertEqual(data['topics'][0]['name'], 'math')
        
        self.assertIn('heatmap', data)
