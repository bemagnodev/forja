from django.test import TestCase
from api.models import Contest, Problem
# Create your tests here.

class ProblemStateMachineTest(TestCase):
    def setUp(self):
        # roda antes de cada teste 
        self.contest = Contest.objects.create(
            external_id=999999, name="Contest Teste", contest_type='PRACTICE'
        )
        self.problem = Problem.objects.create(
            contest=self.contest, index="A", name="Questão Teste"
        )

    def test_wa_does_not_overwrite_ac(self):
        """
        Cenário: Submeti um AC e depois um WA no memso problema
        Expectativa: Um WA submetido hoje não pode apagar um AC conquistado ontem.
        """
        # 1. O usuário submete um AC (Resolve a questão)
        self.problem.update_state_from_submission(is_after=True, is_team_submission=False, verdict='OK')
        
        # Verificamos se ficou verde
        self.assertEqual(self.problem.resolution_status, 'SOLVED_PRACTICE')

        # 2. Dias depois, o usuário testa um código novo e toma WA (Erro)
        self.problem.update_state_from_submission(is_after=True, is_team_submission=False, verdict='WRONG_ANSWER')

        # 3. O MOMENTO DA VERDADE: O status TEM que continuar verde
        self.assertEqual(
            self.problem.resolution_status, 
            'SOLVED_PRACTICE', 
            "ERRO CRÍTICO: Um WA apagou o nosso AC anterior!"
        )

    def test_live_wa_creates_pending_debt(self):
        """
        Cenário: Tentei na prova e errei. 
        Expectativa: A Live Performance vira FAILED e o status vira PENDING.
        """
        self.problem.update_state_from_submission(is_after=False, is_team_submission=False, verdict='WRONG_ANSWER')
        
        self.assertEqual(self.problem.live_performance, 'FAILED')
        self.assertEqual(self.problem.resolution_status, 'PENDING')

    def test_team_ac_creates_debt_then_upsolved(self):
        """
        Cenário : O time fez na prova, mas você upsolva depois.
        Expectativa: Começa como AC_TEAM, depois vira UPSOLVED.
        """
        # 1. Acontece na prova (Time resolveu)
        self.problem.update_state_from_submission(is_after=False, is_team_submission=True, verdict='OK')
        self.assertEqual(self.problem.live_performance, 'AC_TEAM')
        
        # 2. Acontece depois (Você estuda e submete)
        self.problem.update_state_from_submission(is_after=True, is_team_submission=False, verdict='OK')
        
        # O momento da verdade: A dívida foi paga?
        self.assertEqual(self.problem.resolution_status, 'UPSOLVED')

    def test_unattempted_to_upsolved(self):
        """
        Cenário Fantasma: Problema estava no contest, mas você não tentou. Depois você resolve.
        Expectativa: Vai de UNATTEMPTED para UPSOLVED.
        """
        # Forçando o status fantasma (criado pelo Standings da API)
        self.problem.live_performance = 'UNATTEMPTED'
        self.problem.save()

        # Você faz o Upsolving dias depois
        self.problem.update_state_from_submission(is_after=True, is_team_submission=False, verdict='OK')
        
        self.assertEqual(self.problem.resolution_status, 'UPSOLVED')

    def test_solved_live_is_never_downgraded(self):
        """
        Cenário: O usuário resolve na prova (SOLVED_LIVE). Dias depois, manda outro AC pra testar algo.
        Expectativa: O status NÃO PODE ser rebaixado para UPSOLVED ou SOLVED_PRACTICE.
        """
        # 1. AC durante a prova
        self.problem.update_state_from_submission(is_after=False, is_team_submission=False, verdict='OK')
        self.assertEqual(self.problem.resolution_status, 'SOLVED_LIVE')
        
        # 2. Manda outro código certinho dias depois
        self.problem.update_state_from_submission(is_after=True, is_team_submission=False, verdict='OK')
        
        # 3. Tem que continuar SOLVED_LIVE
        self.assertEqual(
            self.problem.resolution_status, 
            'SOLVED_LIVE',
            "ERRO: Um Upsolve apagou o status de SOLVED_LIVE do usuário!"
        )

    def test_team_ac_creates_pending_debt(self):
        """
        Cenário: O time manda o AC na prova, mas a flag 'fui eu' não está marcada.
        Expectativa: Live Performance = AC_TEAM, mas Resolution Status = PENDING (Dívida).
        """
        self.problem.update_state_from_submission(is_after=False, is_team_submission=True, verdict='OK')
        
        self.assertEqual(self.problem.live_performance, 'AC_TEAM')
        self.assertEqual(
            self.problem.resolution_status, 
            'PENDING',
            "ERRO: A questão do time foi marcada como resolvida, mas o usuário ainda tem que estudá-la!"
        )