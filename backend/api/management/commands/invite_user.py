from django.core.management.base import BaseCommand
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from api.models import User

class Command(BaseCommand):
    help = 'Cria ou convida um usuário gerando um link seguro e temporário para ele definir a própria senha'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username do novo usuário ou membro existente')
        parser.add_argument('--cf_handle', type=str, default='', help='Handle do Codeforces (opcional)')
        parser.add_argument('--atcoder_handle', type=str, default='', help='Handle do AtCoder (opcional)')
        parser.add_argument('--email', type=str, default='', help='E-mail do usuário (opcional)')
        parser.add_argument('--base_url', type=str, default='https://forja-cp.vercel.app', help='URL base do frontend (padrão: https://forja-cp.vercel.app)')

    def handle(self, *args, **options):
        username = options['username']
        cf_handle = options['cf_handle'] or None
        atcoder_handle = options['atcoder_handle'] or None
        email = options['email'] or ''
        base_url = options['base_url'].rstrip('/')

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'cf_handle': cf_handle,
                'atcoder_handle': atcoder_handle,
            }
        )

        if created:
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Usuário '{username}' criado no banco de dados!"))
        else:
            # Atualiza handles caso tenham sido passados
            if cf_handle:
                user.cf_handle = cf_handle
            if atcoder_handle:
                user.atcoder_handle = atcoder_handle
            if email:
                user.email = email
            user.save()
            self.stdout.write(self.style.WARNING(f"ℹ️ Usuário '{username}' já existe. Gerando novo link de definição de senha..."))

        # Gerar Token Criptográfico Seguro do Django
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        invite_link = f"{base_url}/set-password?uid={uid}&token={token}"

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("🔗 LINK DE CONVITE / DEFINIÇÃO DE SENHA GERADO COM SUCESSO:"))
        self.stdout.write(f"\n   {invite_link}\n")
        self.stdout.write("=" * 70)
        self.stdout.write("Copie e envie esse link para o membro da equipe.")
        self.stdout.write("Esse link expira automaticamente e torna-se inválido após o uso.\n")
