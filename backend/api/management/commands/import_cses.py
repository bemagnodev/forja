from django.core.management.base import BaseCommand
from api.models import Contest, Problem, Submission
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
import os
from dotenv import load_dotenv
import zlib
import math

class Command(BaseCommand):
    help = 'Importa dados do CSES com Rating Estimado e IDs estáveis'

    def handle(self, *args, **options):
        load_dotenv()
        token = os.getenv('CSES_SESSION')
        
        if not token:
            self.stdout.write(self.style.ERROR("ERRO: Token não encontrado no .env"))
            return

        # === Mapeamento de Tags e Contests Ids ===
        # ID Base: 900.000 (Longe do Codeforces)
        # Formato: "Nome da Seção": [ID_FIXO, [TAGS]]
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

        def get_stable_id(text):
            """Gera um ID numérico fixo baseado no texto (Determinístico)"""
            return zlib.adler32(text.encode('utf-8'))

        def estimate_rating(solve_count):
            """
            Estima rating baseado na popularidade.
            Fórmula empírica: Menos soluções = Maior rating.
            Base: 150k solutions ~ 800 rating
                  500 solutions ~ 3000 rating
            """
            if solve_count == 0: return 0
            try:
                log_val = math.log10(solve_count)
                rating = 3800 - (550 * log_val)
                return max(800, min(3500, int(round(rating / 100) * 100)))
            except:
                return 800

        self.stdout.write("Iniciando Importação CSES V3...")
        
        url = "https://cses.fi/problemset/"
        cookies = {'PHPSESSID': token}

        try:
            response = requests.get(url, cookies=cookies, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            content_div = soup.find('div', class_='content')
            
            # Pega todas as seções
            sections = content_div.find_all('h2')
            
            count_probs = 0

            for section in sections:
                section_name = section.text.strip()
                
                # Se acharmos uma seção nova que não mapeamos, avisamos e pulamos (segurança)
                if section_name not in CSES_MAP:
                    self.stdout.write(self.style.WARNING(f"Seção nova encontrada e ignorada: {section_name}"))
                    continue

                # Pega ID e Tags do nosso mapa manual
                fixed_id, section_tags = CSES_MAP[section_name]

                # Cria Contest
                contest, _ = Contest.objects.get_or_create(
                    external_id=fixed_id,
                    defaults={
                        'name': f"CSES - {section_name}",
                        'is_team': False,
                        'start_time': timezone.now(),
                        'platform': Contest.Platform.CSES
                    }
                )

                # Busca a lista de tarefas
                task_list = section.find_next_sibling('ul', class_='task-list')
                if not task_list: continue
                
                tasks = task_list.find_all('li', class_='task')
                self.stdout.write(f"Processando {section_name} (ID: {fixed_id})...")

                for task in tasks:
                    link = task.find('a')
                    name = link.text
                    href = link['href']
                    
                    try:
                        prob_id_str = href.split('/')[-1] # ex: 1068
                        prob_index = f"CSES-{prob_id_str}"
                    except: continue

                    # Rating
                    solve_count = 0
                    detail = task.find('span', class_='detail')
                    if detail:
                        try:
                            solve_count = int(detail.text.split('/')[0].strip())
                        except: pass
                    
                    estimated_rating = estimate_rating(solve_count)

                    # Status
                    icon = task.find('span', class_='task-score')
                    classes = icon.get('class', [])
                    verdict = 'OK' if 'full' in classes else ('WRONG_ANSWER' if 'zero' in classes else None)

                    # 2. Salvar Problema
                    problem, _ = Problem.objects.update_or_create(
                        contest=contest,
                        index=prob_index,
                        defaults={
                            'name': name,
                            'rating': estimated_rating,
                            'tags': section_tags
                        }
                    )

                    # 3. Lógica de Atualização do Status
                    if verdict == 'OK':
                         if not problem.is_solved:
                            problem.is_solved = True
                            problem.save()

                    # 4. Salvar Submissão
                    if verdict:
                        # Gera ID da submissão baseado no ID do problema (offset para segurança)
                        fake_sub_id = int(prob_id_str) + 900000000
                        
                        Submission.objects.update_or_create(
                            submission_id=fake_sub_id,
                            defaults={
                                'problem': problem,
                                'verdict': verdict,
                                'creation_time': timezone.now()
                            }
                        )
                        count_probs += 1

            self.stdout.write(self.style.SUCCESS(f"✅ CSES Finalizado! {count_probs} submissões sincronizadas."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro Crítico: {e}"))