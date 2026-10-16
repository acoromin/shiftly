from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from employees.models import EmployeeProfile
from scheduling.models import Shift
from timeclock.models import TimeClockEntry


class Incident(models.Model):
    class IncidentType(models.TextChoices):
        MISSING_CLOCK_IN = 'missing_clock_in', 'Falta el fichaje de entrada'
        MISSING_CLOCK_OUT = 'missing_clock_out', 'Falta el fichaje de salida'
        CLOCK_ERROR = 'clock_error', 'Error de fichaje'
        OTHER = 'other', 'Otro problema'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        APPROVED = 'approved', 'Aprobado'
        REJECTED = 'rejected', 'Rechazado'
        RESOLVED = 'resolved', 'Resuelto'

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name='incidents', verbose_name='empleado')
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='incidents',
        verbose_name='empresa',
    )
    date = models.DateField('fecha')
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, blank=True, null=True, related_name='incidents', verbose_name='turno')
    timeclock_entry = models.ForeignKey(
        TimeClockEntry,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='incidents',
        verbose_name='fichaje',
    )
    incident_type = models.CharField('tipo de incidencia', max_length=30, choices=IncidentType.choices)
    description = models.TextField('descripción')
    status = models.CharField('estado', max_length=20, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_incidents',
        verbose_name='creado por',
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='resolved_incidents',
        verbose_name='resuelto por',
    )
    resolved_at = models.DateTimeField('resuelto el', blank=True, null=True)
    resolution_comment = models.TextField('comentario de resolución', blank=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'incidencia'
        verbose_name_plural = 'incidencias'
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['status', 'date']),
        ]

    def __str__(self):
        return f'{self.employee} · {self.get_incident_type_display()} · {self.date:%d/%m/%Y}'

    def clean(self):
        errors = {}
        if (
            self.company_id
            and self.employee_id
            and self.employee.company_id
            and self.employee.company_id != self.company_id
        ):
            errors['employee'] = 'El empleado debe pertenecer a la misma empresa que la incidencia.'
        if (
            self.company_id
            and self.shift_id
            and self.shift.company_id
            and self.shift.company_id != self.company_id
        ):
            errors['shift'] = 'El turno debe pertenecer a la misma empresa que la incidencia.'
        if (
            self.company_id
            and self.timeclock_entry_id
            and self.timeclock_entry.company_id
            and self.timeclock_entry.company_id != self.company_id
        ):
            errors['timeclock_entry'] = 'El fichaje debe pertenecer a la misma empresa que la incidencia.'
        if errors:
            raise ValidationError(errors)

    def resolve(self, *, status, user, comment=''):
        if status not in {self.Status.APPROVED, self.Status.REJECTED, self.Status.RESOLVED}:
            raise ValueError('Estado de resolución no válido.')
        self.status = status
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_comment = comment
        self.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_comment', 'updated_at'])

# Create your models here.
