import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class BusinessConfig(models.Model):
    name = models.CharField('nombre del negocio', max_length=120, default='Xarlot')
    public_wifi_ip = models.GenericIPAddressField('IP pública del WiFi', blank=True, null=True)
    qr_static_token_hash = models.CharField('token protegido del QR', max_length=256, blank=True)
    timezone = models.CharField('zona horaria', max_length=64, default='Europe/Madrid')
    clock_tolerance_minutes = models.PositiveSmallIntegerField('minutos de tolerancia', default=5)
    maintenance_enabled = models.BooleanField('modo mantenimiento activado', default=False)
    maintenance_scheduled_start = models.DateTimeField(
        'inicio programado del mantenimiento',
        blank=True,
        null=True,
    )
    maintenance_scheduled_end = models.DateTimeField(
        'fin programado del mantenimiento',
        blank=True,
        null=True,
    )
    maintenance_reason = models.CharField('motivo del mantenimiento', max_length=240, blank=True)
    maintenance_message = models.TextField(
        'mensaje para los trabajadores',
        default=(
            'La aplicación está temporalmente en mantenimiento. Normalmente estas tareas '
            'se realizan los lunes, día de cierre del bar. Si necesitas realizar alguna '
            'gestión urgente, contacta con el administrador.'
        ),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='updated_business_configs',
    )
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        verbose_name = 'configuración del negocio'
        verbose_name_plural = 'configuración del negocio'

    def __str__(self):
        return self.name

    def clean(self):
        if self.maintenance_scheduled_end and not self.maintenance_scheduled_start:
            raise ValidationError({
                'maintenance_scheduled_start': 'Indica una fecha de inicio para la programación.',
            })
        if (
            self.maintenance_scheduled_start
            and self.maintenance_scheduled_end
            and self.maintenance_scheduled_end <= self.maintenance_scheduled_start
        ):
            raise ValidationError({
                'maintenance_scheduled_end': 'La fecha de fin debe ser posterior al inicio.',
            })

    @classmethod
    def get_solo(cls):
        config, _ = cls.objects.get_or_create(pk=1, defaults={'name': 'Xarlot'})
        return config

    def set_qr_token(self, raw_token):
        self.qr_static_token_hash = make_password(raw_token)

    def check_qr_token(self, raw_token):
        if not raw_token or not self.qr_static_token_hash:
            return False
        return check_password(raw_token, self.qr_static_token_hash)

    def is_maintenance_active(self, at=None):
        at = at or timezone.now()
        if self.maintenance_enabled:
            return True
        if not self.maintenance_scheduled_start or at < self.maintenance_scheduled_start:
            return False
        return not self.maintenance_scheduled_end or at < self.maintenance_scheduled_end

    @property
    def has_scheduled_maintenance(self):
        return bool(self.maintenance_scheduled_start)

    @staticmethod
    def generate_qr_token():
        return secrets.token_urlsafe(48)

# Create your models here.
