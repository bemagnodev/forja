import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# ==========================================

from api.models import Contest, Problem, Submission
from django.db.models import Count

print("=== 🏥 RELATÓRIO DE SAÚDE DA FORJA ===")


# 1. Contagem Geral
total_contests = Contest.objects.count()
total_problems = Problem.objects.count()
total_subs = Submission.objects.count()

print(f"\n📊 TOTAIS:")
print(f"  - Contests:    {total_contests}")
print(f"  - Problemas:   {total_problems}")
print(f"  - Submissões:  {total_subs}")

# 2. Distribuição por Plataforma
print(f"\n🌍 PLATAFORMAS:")
for platform in ['CF', 'CSES']:
    c_count = Contest.objects.filter(platform=platform).count()
    p_count = Problem.objects.filter(contest__platform=platform).count()
    print(f"  - {platform}: {c_count} Contests | {p_count} Problemas")

# 3. Consistência do 'is_solved'
solved_db = Problem.objects.filter(is_solved=True).count()
real_solved = Problem.objects.filter(submissions__verdict='OK').distinct().count()

print(f"\n✅ CONSISTÊNCIA DE RESOLVIDOS:")
print(f"  - Marcados no BD (is_solved=True): {solved_db}")
print(f"  - Real (tem submissão OK):         {real_solved}")

if solved_db == real_solved:
    print("  STATUS: INTEGRO 🟢")
else:
    print(f"  STATUS: INCONSISTENTE 🔴 (Diferença de {abs(solved_db - real_solved)})")

# 4. Checagem de Órfãos (Submissão sem Problema ou Problema sem Contest)
orphans = Submission.objects.filter(problem__isnull=True).count()
print(f"\n👻 DADOS ÓRFÃOS: {orphans}")

print("\n=== FIM DO DIAGNÓSTICO ===")