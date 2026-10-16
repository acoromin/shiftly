from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from employees.models import EmployeeProfile
from scheduling.models import Shift


class TimeClockEntry(models.Model):
    class EntryType(models.TextChoices):
        IN = 'in', 'Entrada'
        OUT = 'out', 'Salida'

    class Status(models.TextChoices):
        VALID = 'valid', 'Válido'
        BLOCKED_IP = 'blocked_ip', 'Bloqueado por IP'
        INVALID_QR = 'invalid_qr', 'QR no válido'
        MANUAL = 'manual', 'Manual'
        CORRECTED = 'corrected', 'Corregido'

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name='timeclock_entries',
        verbose_name='empleado',
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='timeclock_entries',
        verbose_name='empresa',
    )
    workplace = models.ForeignKey(
        'companies.Workplace',
        on_delete=models.PROTECT,
        related_name='timeclock_entries',
        verbose_name='centro de trabajo',
        blank=True,
        null=True,
    )
    entry_type = models.CharField('tipo', max_length=10, choices=EntryType.choices)
    timestamp = models.DateTimeField('fecha y hora')
    detected_ip = models.GenericIPAddressField('IP detectada', blank=True, null=True)
    user_agent = models.TextField('navegador', blank=True)
    qr_token_label = models.CharField('identificador del QR', max_length=80, blank=True)
    status = models.CharField('estado', max_length=20, choices=Status.choices, default=Status.VALID)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_timeclock_entries',
        verbose_name='creado por',
    )
    manual_reason = models.TextField('motivo de la corrección', blank=True)
    related_shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        related_name='timeclock_entries',
        blank=True,
        null=True,
        verbose_name='turno relacionado',
    )
    created_at = models.DateTimeField('creado el', auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'fichaje'
        verbose_name_plural = 'fichajes'
        indexes = [
            models.Index(fields=['employee', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.employee} · {self.get_entry_type_display()} · {self.timestamp:%d/%m/%Y %H:%M}'

    def clean(self):
        errors = {}
        if self.status == self.Status.MANUAL and not self.manual_reason.strip():
            errors['manual_reason'] = 'El motivo es obligatorio para fichajes manuales.'
        if self.status == self.Status.CORRECTED and not self.manual_reason.strip():
            errors['manual_reason'] = 'El motivo es obligatorio para fichajes corregidos.'
        if (
            self.company_id
            and self.employee_id
            and self.employee.company_id
            and self.employee.company_id != self.company_id
        ):
            errors['employee'] = 'El empleado debe pertenecer a la misma empresa que el fichaje.'
        if self.workplace_id and not self.company_id:
            errors['company'] = 'Indica la empresa para asignar un centro de trabajo.'
        elif self.workplace_id and self.workplace.company_id != self.company_id:
            errors['workplace'] = 'El centro de trabajo debe pertenecer a la misma empresa que el fichaje.'
        if (
            self.company_id
            and self.related_shift_id
            and self.related_shift.company_id
            and self.related_shift.company_id != self.company_id
        ):
            errors['related_shift'] = 'El turno relacionado debe pertenecer a la misma empresa que el fichaje.'
        if (
            self.related_shift_id
            and self.employee_id
            and self.related_shift.employee_id != self.employee_id
        ):
            errors['related_shift'] = 'El turno relacionado debe pertenecer al mismo empleado que el fichaje.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
