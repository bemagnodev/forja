from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from api.models import User

class Command(BaseCommand):
    help = 'Gera um link seguro e temporário para um usuário existente redefinir sua senha'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username do usuário existente')
        default_frontend_url = getattr(settings, 'FRONTEND_URL', 'https://forja-cp.vercel.app')
        parser.add_argument(
            '--base_url',
            type=str,
            default=default_frontend_url,
            help=f'URL base do frontend (padrão: {default_frontend_url})'
        )

    def handle(self, *args, **options):
        username = options['username']
        base_url = options['base_url'].rstrip('/')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"O usuário '{username}' não foi encontrado no banco de dados.")

        # Gerar Token Criptográfico Seguro do Django
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        reset_link = f"{base_url}/set-password?uid={uid}&token={token}"

        self.stdout.write(self.style.SUCCESS(f"ℹ️ Usuário '{username}' localizado."))
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("🔗 LINK DE DEFINIÇÃO / REDEFINIÇÃO GERADO COM SUCESSO:"))
        self.stdout.write(f"\n   {reset_link}\n")
        self.stdout.write("=" * 70)
        self.stdout.write("Copie e envie esse link para o membro da equipe.")
        if user.is_active:
            self.stdout.write("A senha atual continua ativa até que este link seja utilizado.\n")
        else:
            self.stdout.write("A conta permanece inativa até que este link seja utilizado para definir a senha.\n")
