from django.core.management.base import BaseCommand
from api.models import User

class Command(BaseCommand):
    help = 'Cria usuários iniciais mockados para o MVP multi-usuário'

    def handle(self, *args, **kwargs):
        users_data = [
            {'username': 'membro1', 'password': 'password123', 'cf_handle': 'tourist'},
            {'username': 'membro2', 'password': 'password123', 'cf_handle': 'Benq'},
            {'username': 'membro3', 'password': 'password123', 'cf_handle': 'jiangly'},
        ]
        
        created = 0
        for data in users_data:
            if not User.objects.filter(username=data['username']).exists():
                user = User.objects.create_user(
                    username=data['username'],
                    password=data['password'],
                    cf_handle=data['cf_handle']
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Usuário {user.username} criado com sucesso.'))
        
        if created == 0:
            self.stdout.write(self.style.WARNING('Nenhum novo usuário criado (já existem).'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{created} usuários criados.'))
