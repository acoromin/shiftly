from django.core.management.base import BaseCommand, CommandError

from companies.models import Workplace


class Command(BaseCommand):
    help = 'Configura la IP y genera un token QR para un centro de trabajo.'

    def add_arguments(self, parser):
        parser.add_argument('--wifi-ip', required=True, help='IP publica autorizada del WiFi del bar.')
        parser.add_argument('--workplace-id', type=int, required=True, help='ID del centro de trabajo.')
        parser.add_argument(
            '--base-url',
            default='http://127.0.0.1:8000',
            help='URL base donde corre Xarlot.',
        )

    def handle(self, *args, **options):
        try:
            workplace = Workplace.objects.get(pk=options['workplace_id'], is_active=True)
        except Workplace.DoesNotExist as exc:
            raise CommandError('El centro indicado no existe o está inactivo.') from exc
        token = Workplace.generate_qr_token()
        workplace.public_wifi_ip = options['wifi_ip']
        workplace.set_qr_token(token)
        workplace.full_clean()
        workplace.save(update_fields=['public_wifi_ip', 'qr_token_hash'])

        base_url = options['base_url'].rstrip('/')
        self.stdout.write(self.style.SUCCESS('Configuracion de fichaje actualizada.'))
        self.stdout.write(f'Centro: {workplace}')
        self.stdout.write(f'IP autorizada: {workplace.public_wifi_ip}')
        self.stdout.write('URL para imprimir como QR:')
        self.stdout.write(f'{base_url}/fichar/?token={token}')
