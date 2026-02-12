from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
from dotenv import load_dotenv
import time

class Command(BaseCommand):
    help = 'Roda o ETL completo (Codeforces + CSES) lendo configurações do .env'

    def handle(self, *args, **options):
        load_dotenv()
        
        # 1. Configurações
        cf_handle = os.getenv('CODEFORCES_HANDLE')
        cses_token = os.getenv('CSES_SESSION')

        self.stdout.write(self.style.MIGRATE_HEADING("=== INICIANDO SINCRONIZAÇÃO TOTAL DA FORJA ==="))

        # 2. Executa Codeforces
        if cf_handle:
            self.stdout.write(f"\n🚀 Disparando ETL Codeforces para: {cf_handle}")
            try:
                # Chama o outro comando internamente
                call_command('import_cf', handle=cf_handle)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Falha no Codeforces: {e}"))
        else:
            self.stdout.write(self.style.WARNING("Pulei Codeforces (CODEFORCES_HANDLE não definido no .env)"))

        time.sleep(1)

        # 3. Executa CSES
        if cses_token:
            self.stdout.write(f"\n🌲 Disparando ETL CSES...")
            try:
                call_command('import_cses')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Falha no CSES: {e}"))
        else:
            self.stdout.write(self.style.WARNING("Pulei CSES (CSES_SESSION não definido no .env)"))

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== SINCRONIZAÇÃO CONCLUÍDA ==="))