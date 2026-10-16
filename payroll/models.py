from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from employees.models import EmployeeProfile


class MonthlyHoursSummary(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name='monthly_summaries', verbose_name='empleado')
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='monthly_summaries',
        verbose_name='empresa',
    )
    year = models.PositiveSmallIntegerField('año')
    month = models.PositiveSmallIntegerField('mes')
    contracted_hours = models.DecimalField('horas contratadas', max_digits=7, decimal_places=2, default=0)
    planned_hours = models.DecimalField('horas planificadas', max_digits=7, decimal_places=2, default=0)
    valid_clocked_hours = models.DecimalField('horas fichadas válidas', max_digits=7, decimal_places=2, default=0)
    pending_review_hours = models.DecimalField('horas pendientes de revisión', max_digits=7, decimal_places=2, default=0)
    detected_overtime_hours = models.DecimalField('horas extra detectadas', max_digits=7, decimal_places=2, default=0)
    approved_overtime_hours = models.DecimalField('horas extra aprobadas', max_digits=7, decimal_places=2, default=0)
    approved_vacation_days = models.PositiveSmallIntegerField('días de vacaciones aprobados', default=0)
    approved_day_off_days = models.PositiveSmallIntegerField('días libres aprobados', default=0)
    absence_days = models.PositiveSmallIntegerField('días de ausencia', default=0)
    pending_incidents_count = models.PositiveSmallIntegerField('incidencias pendientes', default=0)
    observations = models.TextField('observaciones', blank=True)
    calculated_at = models.DateTimeField('calculado el', auto_now=True)

    class Meta:
        unique_together = ('employee', 'year', 'month')
        ordering = ['year', 'month', 'employee__full_name']
        verbose_name = 'resumen mensual de horas'
        verbose_name_plural = 'resúmenes mensuales de horas'

    def __str__(self):
        return f'{self.employee} · {self.month:02d}/{self.year}'

    def clean(self):
        if self.company_id and self.employee_id and self.employee.company_id != self.company_id:
            raise ValidationError({'employee': 'El empleado debe pertenecer a la empresa del resumen.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PayrollDraft(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        EXPORTED = 'exported', 'Exportado'
        CLOSED = 'closed', 'Cerrado'

    year = models.PositiveSmallIntegerField('año')
    month = models.PositiveSmallIntegerField('mes')
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='payroll_drafts',
        verbose_name='empresa',
    )
    status = models.CharField('estado', max_length=20, choices=Status.choices, default=Status.DRAFT)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='generated_payroll_drafts',
        verbose_name='generado por',
    )
    generated_at = models.DateTimeField('generado el', auto_now_add=True)
    notes = models.TextField('notas', blank=True)

    class Meta:
        ordering = ['-year', '-month', '-generated_at']
        verbose_name = 'borrador de pre-nómina'
        verbose_name_plural = 'borradores de pre-nómina'

    def __str__(self):
        return f'Borrador {self.month:02d}/{self.year}'

    def clean(self):
        if self.pk and self.company_id:
            foreign_lines = self.lines.filter(company__isnull=False).exclude(company_id=self.company_id)
            foreign_employees = self.lines.exclude(employee__company_id=self.company_id)
            if foreign_lines.exists() or foreign_employees.exists():
                raise ValidationError({'company': 'La empresa del borrador debe coincidir con sus lineas y empleados.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PayrollDraftLine(models.Model):
    draft = models.ForeignKey(PayrollDraft, on_delete=models.CASCADE, related_name='lines', verbose_name='borrador')
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name='payroll_draft_lines', verbose_name='empleado')
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='payroll_draft_lines',
        verbose_name='empresa',
    )
    contracted_hours = models.DecimalField('horas contratadas', max_digits=7, decimal_places=2, default=0)
    planned_hours = models.DecimalField('horas planificadas', max_digits=7, decimal_places=2, default=0)
    valid_clocked_hours = models.DecimalField('horas fichadas válidas', max_digits=7, decimal_places=2, default=0)
    pending_review_hours = models.DecimalField('horas pendientes de revisión', max_digits=7, decimal_places=2, default=0)
    detected_overtime_hours = models.DecimalField('horas extra detectadas', max_digits=7, decimal_places=2, default=0)
    approved_overtime_hours = models.DecimalField('horas extra aprobadas', max_digits=7, decimal_places=2, default=0)
    approved_vacation_days = models.PositiveSmallIntegerField('días de vacaciones aprobados', default=0)
    approved_day_off_days = models.PositiveSmallIntegerField('días libres aprobados', default=0)
    absence_days = models.PositiveSmallIntegerField('días de ausencia', default=0)
    pending_incidents_count = models.PositiveSmallIntegerField('incidencias pendientes', default=0)
    observations = models.TextField('observaciones', blank=True)

    class Meta:
        ordering = ['employee__full_name']
        verbose_name = 'línea de borrador'
        verbose_name_plural = 'líneas de borrador'

    def __str__(self):
        return f'{self.employee} · {self.draft}'

    def clean(self):
        if self.company_id:
            if self.employee_id and self.employee.company_id != self.company_id:
                raise ValidationError('La empresa de la linea debe coincidir con la del empleado.')
            if self.draft_id and self.draft.company_id != self.company_id:
                # Non-field errors also work in the admin inline, where draft is excluded.
                raise ValidationError('La empresa de la linea debe coincidir con la del borrador.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
