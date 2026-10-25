from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import SecurityThrottle


class Command(BaseCommand):
    help = 'Elimina contadores de intentos antiguos; programar diariamente en cada entorno.'

    def handle(self, *args, **options):
        deleted, _details = SecurityThrottle.objects.filter(
            updated_at__lt=timezone.now() - timedelta(days=1),
        ).delete()
        self.stdout.write(f'Contadores eliminados: {deleted}')
