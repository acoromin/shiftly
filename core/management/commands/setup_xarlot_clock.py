from django.core.management.base import BaseCommand

from core.models import BusinessConfig


class Command(BaseCommand):
    help = 'Configura la IP del bar y genera un token QR estatico para Xarlot.'

    def add_arguments(self, parser):
        parser.add_argument('--wifi-ip', required=True, help='IP publica autorizada del WiFi del bar.')
        parser.add_argument(
            '--base-url',
            default='http://127.0.0.1:8000',
            help='URL base donde corre Xarlot.',
        )

    def handle(self, *args, **options):
        config = BusinessConfig.get_solo()
        token = BusinessConfig.generate_qr_token()
        config.public_wifi_ip = options['wifi_ip']
        config.set_qr_token(token)
        config.save()

        base_url = options['base_url'].rstrip('/')
        self.stdout.write(self.style.SUCCESS('Configuracion de fichaje actualizada.'))
        self.stdout.write(f'IP autorizada: {config.public_wifi_ip}')
        self.stdout.write('URL para imprimir como QR:')
        self.stdout.write(f'{base_url}/fichar/?token={token}')
