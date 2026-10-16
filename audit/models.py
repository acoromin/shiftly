from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CLOCK_IN = 'clock_in', 'Fichaje entrada'
        CLOCK_OUT = 'clock_out', 'Fichaje salida'
        CLOCK_BLOCKED_IP = 'clock_blocked_ip', 'Fichaje bloqueado por IP'
        CLOCK_INVALID_QR = 'clock_invalid_qr', 'Fichaje bloqueado por QR no válido'
        CLOCK_MANUAL = 'clock_manual', 'Fichaje manual'
        CLOCK_CORRECTED = 'clock_corrected', 'Fichaje corregido'
        MAINTENANCE_ENABLED = 'maintenance_enabled', 'Mantenimiento activado'
        MAINTENANCE_DISABLED = 'maintenance_disabled', 'Mantenimiento desactivado'
        MAINTENANCE_SCHEDULED = 'maintenance_scheduled', 'Mantenimiento programado'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='audit_logs',
        verbose_name='usuario',
    )
    action = models.CharField('acción', max_length=80, choices=Action.choices)
    entity_type = models.CharField('tipo de registro', max_length=120, blank=True)
    entity_id = models.CharField('identificador del registro', max_length=80, blank=True)
    old_value = models.JSONField('valor anterior', blank=True, null=True)
    new_value = models.JSONField('valor nuevo', blank=True, null=True)
    ip_address = models.GenericIPAddressField('dirección IP', blank=True, null=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'registro de auditoría'
        verbose_name_plural = 'registros de auditoría'

    def __str__(self):
        return f'{self.get_action_display()} · {self.created_at:%d/%m/%Y %H:%M}'

# Create your models here.
