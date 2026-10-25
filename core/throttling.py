from datetime import timedelta
from hashlib import sha256

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .network import get_client_ip
from .models import SecurityThrottle


def consume_attempt(scope, identity, *, limit, window_seconds):
    digest = sha256(f'{scope}\0{identity}'.encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        counter, _created = SecurityThrottle.objects.select_for_update().get_or_create(
            key=digest, defaults={'window_started_at': now},
        )
        if now - counter.window_started_at >= timedelta(seconds=window_seconds):
            counter.window_started_at = now
            counter.attempts = 0
        if counter.attempts >= limit:
            return False
        counter.attempts += 1
        counter.save(update_fields=['window_started_at', 'attempts', 'updated_at'])
    return True


class LoginThrottleMixin:
    def clean(self):
        ip = get_client_ip(self.request)
        if not ip:
            raise ValidationError('No se pudo validar la conexion.', code='invalid_client_ip')
        username = str(self.data.get('username', '')).strip().casefold()[:150]
        if not consume_attempt('login-ip', ip, limit=60, window_seconds=300):
            raise ValidationError('Demasiados intentos. Prueba dentro de unos minutos.', code='login_limited')
        if not consume_attempt('login-user', f'{ip}\0{username}', limit=10, window_seconds=300):
            raise ValidationError('Demasiados intentos. Prueba dentro de unos minutos.', code='login_limited')
        return super().clean()
