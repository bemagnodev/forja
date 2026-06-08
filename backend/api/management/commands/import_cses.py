from django.core.management.base import BaseCommand
from api.models import Contest, Problem, Submission, User, PlatformChoices, UserProblemTracking
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
import os
import zlib
import math

class Command(BaseCommand):
    help = 'Importa problemas e histórico do CSES baseado nos usuários com cses_token'

    def handle(self, *args, **options):
        # Encontra usuários com token configurado
        users = User.objects.exclude(cses_token__isnull=True).exclude(cses_token__exact='')
        
        if not users.exists():
            self.stdout.write(self.style.WARNING("Nenhum usuário com cses_token encontrado."))
            return

        # === Mapeamento de Tags e Contests Ids ===
        CSES_MAP = {
            "General":                  (900000, ["ad-hoc", "implementation"]), 
            "Introductory Problems":    (900001, ["implementation", "math"]),
            "Sorting and Searching":    (900002, ["sortings", "binary search", "two pointers"]),
            "Dynamic Programming":      (900003, ["dp"]),
            "Graph Algorithms":         (900004, ["graphs", "shortest paths", "dfs and similar"]),
            "Range Queries":            (900005, ["data structures", "trees"]),
            "Tree Algorithms":          (900006, ["trees", "dfs and similar"]),
            "Mathematics":              (900007, ["math", "number theory"]),
            "String Algorithms":        (900008, ["strings"]),
            "Geometry":                 (900009, ["geometry"]),
            "Advanced Techniques":      (900010, ["bitmasks", "meet-in-the-middle"]),
            "Additional Problems":      (900011, ["ad-hoc"]),  
            "Sliding Window Problems":  (900012, ["two pointers", "data structures"]),
            "Bitwise Operations":       (900013, ["bitmasks", "math"]),
            
            "Interactive Problems":     (900014, ["interactive", "ad-hoc"]),
            "Construction Problems":    (900015, ["constructive algorithms"]),
            "Advanced Graph Problems":  (900016, ["graphs", "flows", "cut"]),
            "Counting Problems":        (900017, ["combinatorics", "math"]),
            "Additional Problems I":    (900018, ["ad-hoc", "hard"]),
            "Additional Problems II":   (900019, ["ad-hoc", "hard"])
        }

        def estimate_rating(solve_count):
            if solve_count == 0: return 0
            try:
                log_val = math.log10(solve_count)
                rating = 3800 - (550 * log_val)
                return max(800, min(3500, int(round(rating / 100) * 100)))
            except:
                return 800

        self.stdout.write("Iniciando Importação CSES adaptada para Nova FSM...")
        url = "https://cses.fi/problemset/"

        for user in users:
            self.stdout.write(self.style.MIGRATE_HEADING(f"[{user.username}] Baixando CSES..."))
            cookies = {'PHPSESSID': user.cses_token}
            
            try:
                response = requests.get(url, cookies=cookies, timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                content_div = soup.find('div', class_='content')
                
                if not content_div:
                    self.stdout.write(self.style.ERROR(f"[{user.username}] Não foi possível ler a página. Token expirado?"))
                    continue

                sections = content_div.find_all('h2')
                count_probs = 0

                for section in sections:
                    section_name = section.text.strip()
                    
                    if section_name not in CSES_MAP:
                        self.stdout.write(self.style.WARNING(f"Seção nova ignorada: {section_name}"))
                        continue

                    fixed_id, section_tags = CSES_MAP[section_name]

                    # 1. Cria Contest (Categoria)
                    contest, _ = Contest.objects.get_or_create(
                        platform=PlatformChoices.CSES,
                        platform_id=str(fixed_id),
                        defaults={
                            'name': f"CSES - {section_name}",
                            'start_time': timezone.now()
                        }
                    )

                    task_list = section.find_next_sibling('ul', class_='task-list')
                    if not task_list: continue
                    
                    tasks = task_list.find_all('li', class_='task')

                    for task in tasks:
                        link = task.find('a')
                        name = link.text
                        href = link['href']
                        
                        try:
                            prob_id_str = href.split('/')[-1] # ex: 1068
                        except: continue

                        solve_count = 0
                        detail = task.find('span', class_='detail')
                        if detail:
                            try:
                                solve_count = int(detail.text.split('/')[0].strip())
                            except: pass
                        
                        estimated_rating = estimate_rating(solve_count)

                        icon = task.find('span', class_='task-score')
                        classes = icon.get('class', [])
                        verdict = 'AC' if 'full' in classes else ('WA' if 'zero' in classes else None)

                        # 2. Salvar Problema
                        problem, _ = Problem.objects.update_or_create(
                            platform=PlatformChoices.CSES,
                            platform_id=prob_id_str,
                            defaults={
                                'title': name,
                                'contest': contest,
                                'platform_metadata': {
                                    'official_rating': estimated_rating,
                                    'official_tags': section_tags
                                }
                            }
                        )

                        # 3. Criar Tracking
                        tracking, _ = UserProblemTracking.objects.get_or_create(
                            user=user, 
                            problem=problem
                        )

                        new_sys_status = UserProblemTracking.SystemStatus.UNATTEMPTED

                        if verdict:
                            fake_sub_id = f"CSES_{prob_id_str}_{user.id}"
                            
                            Submission.objects.update_or_create(
                                platform_submission_id=fake_sub_id,
                                defaults={
                                    'problem': problem,
                                    'user': user,
                                    'participant_type': Submission.ParticipantType.PRACTICE,
                                    'verdict': verdict,
                                    'creation_time': timezone.now()
                                }
                            )
                            count_probs += 1
                            
                            if verdict == 'AC':
                                new_sys_status = UserProblemTracking.SystemStatus.PRACTICE_AC
                            else:
                                new_sys_status = UserProblemTracking.SystemStatus.PRACTICE_WA
                        
                        # Atualizar FSM
                        if tracking.system_status != new_sys_status:
                            tracking.system_status = new_sys_status
                            tracking.save()

                self.stdout.write(self.style.SUCCESS(f"[OK] CSES de {user.username} finalizado! {count_probs} interações processadas."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro Crítico processando {user.username}: {e}"))