from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from employees.models import EmployeeProfile


class Shift(models.Model):
    class Position(models.TextChoices):
        WAITER = 'camarero', 'Camarero'
        COOK = 'cocinero', 'Cocinero'

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name='shifts',
        verbose_name='empleado',
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='shifts',
        verbose_name='empresa',
    )
    workplace = models.ForeignKey(
        'companies.Workplace',
        on_delete=models.PROTECT,
        related_name='shifts',
        verbose_name='centro de trabajo',
        blank=True,
        null=True,
    )
    date = models.DateField('fecha')
    start_time = models.TimeField('hora de inicio')
    end_time = models.TimeField('hora de fin')
    planned_break_minutes = models.PositiveSmallIntegerField('minutos de descanso', default=0)
    position = models.CharField('puesto de trabajo', max_length=20, choices=Position.choices, default=Position.WAITER)
    notes = models.TextField('notas', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_shifts',
        blank=True,
        null=True,
        verbose_name='creado por',
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='modified_shifts',
        blank=True,
        null=True,
        verbose_name='modificado por',
    )
    is_active = models.BooleanField('activo', default=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        ordering = ['date', 'start_time', 'employee__full_name']
        verbose_name = 'turno'
        verbose_name_plural = 'turnos'
        indexes = [
            models.Index(fields=['date', 'start_time']),
            models.Index(fields=['employee', 'date']),
        ]

    def __str__(self):
        return f'{self.employee} · {self.date:%d/%m/%Y} {self.start_time:%H:%M}-{self.end_time:%H:%M}'

    @property
    def start_datetime(self):
        return datetime.combine(self.date, self.start_time)

    @property
    def end_datetime(self):
        end = datetime.combine(self.date, self.end_time)
        if end <= self.start_datetime:
            end += timedelta(days=1)
        return end

    @property
    def planned_duration_hours(self):
        duration = self.end_datetime - self.start_datetime
        break_delta = timedelta(minutes=self.planned_break_minutes)
        return max((duration - break_delta).total_seconds() / 3600, 0)

    def clean(self):
        errors = {}
        if self.employee_id and not self.employee.is_active:
            errors['employee'] = 'No se pueden crear turnos para empleados inactivos.'
        if self.company_id and self.employee_id and self.employee.company_id != self.company_id:
            errors['employee'] = 'El empleado debe pertenecer a la misma empresa que el turno.'
        if self.workplace_id and not self.company_id:
            errors['company'] = 'Indica la empresa para asignar un centro de trabajo.'
        elif self.workplace_id and self.workplace.company_id != self.company_id:
            errors['workplace'] = 'El centro de trabajo debe pertenecer a la misma empresa que el turno.'
        if self.planned_break_minutes >= 16 * 60:
            errors['planned_break_minutes'] = 'La pausa prevista no puede cubrir todo el turno.'
        if self.employee_id and self.date and self.start_time and self.end_time and self.is_active:
            overlapping = []
            shifts = Shift.objects.filter(
                employee=self.employee,
                is_active=True,
                date__in=[self.date, self.date - timedelta(days=1), self.date + timedelta(days=1)],
            )
            if self.pk:
                shifts = shifts.exclude(pk=self.pk)
            for shift in shifts:
                if self.start_datetime < shift.end_datetime and self.end_datetime > shift.start_datetime:
                    overlapping.append(str(shift))
            if overlapping:
                errors['employee'] = 'El empleado ya tiene un turno solapado.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

# Create your models here.
