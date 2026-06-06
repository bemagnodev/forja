from django.core.management.base import BaseCommand
from api.models import User

class Command(BaseCommand):
    help = 'Cria usuários iniciais mockados para o MVP multi-usuário'

    def handle(self, *args, **kwargs):
        users_data = [
            {'username': 'bemagno', 'password': 'bccufrj1234', 'cf_handle': 'bemagno'},
            {'username': 'bernardomaia', 'password': 'bccufrj1234', 'cf_handle': 'bernardomaia'},
            {'username': 'ryanbloureiro', 'password': 'bccufrj1234', 'cf_handle': 'ryanbloureiro'},
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
