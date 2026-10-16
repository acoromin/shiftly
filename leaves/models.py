from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from employees.models import EmployeeProfile


class LeaveRequest(models.Model):
    class RequestType(models.TextChoices):
        VACATION = 'vacation', 'Vacaciones'
        DAY_OFF = 'day_off', 'Día libre'
        JUSTIFIED_ABSENCE = 'justified_absence', 'Ausencia justificada'
        MEDICAL_ABSENCE = 'medical_absence', 'Baja médica'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        APPROVED = 'approved', 'Aprobado'
        REJECTED = 'rejected', 'Rechazado'
        CANCELLED = 'cancelled', 'Cancelado'

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name='leave_requests', verbose_name='empleado')
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='leave_requests',
        verbose_name='empresa',
    )
    request_type = models.CharField('tipo de solicitud', max_length=30, choices=RequestType.choices)
    start_date = models.DateField('fecha de inicio')
    end_date = models.DateField('fecha de fin')
    worker_comment = models.TextField('comentario', blank=True)
    status = models.CharField('estado', max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='reviewed_leave_requests',
        verbose_name='revisado por',
    )
    admin_comment = models.TextField('comentario del administrador', blank=True)
    reviewed_at = models.DateTimeField('revisado el', blank=True, null=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        ordering = ['-start_date', '-created_at']
        verbose_name = 'solicitud de vacaciones o día libre'
        verbose_name_plural = 'vacaciones y días libres'
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['status', 'start_date']),
        ]

    def __str__(self):
        return f'{self.employee} · {self.get_request_type_display()} · {self.start_date:%d/%m/%Y}'

    def clean(self):
        errors = {}
        if self.end_date and self.start_date and self.end_date < self.start_date:
            errors['end_date'] = 'La fecha fin no puede ser anterior a la fecha inicio.'
        if (
            self.company_id
            and self.employee_id
            and self.employee.company_id
            and self.employee.company_id != self.company_id
        ):
            errors['employee'] = 'El empleado debe pertenecer a la misma empresa que la solicitud.'
        if self.reviewed_by_id and self.company_id:
            reviewer = getattr(self.reviewed_by, 'employee_profile', None)
            if reviewer and reviewer.company_id != self.company_id:
                errors['reviewed_by'] = 'El revisor debe pertenecer a la misma empresa que la solicitud.'
        if self.employee_id and self.start_date and self.end_date:
            overlapping = LeaveRequest.objects.filter(
                employee=self.employee,
                status__in=[self.Status.PENDING, self.Status.APPROVED],
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                errors['__all__'] = 'Ya existe una solicitud pendiente o aprobada para esas fechas.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @transaction.atomic
    def review(self, *, status, user, comment=''):
        if status not in {self.Status.APPROVED, self.Status.REJECTED}:
            raise ValueError('Estado de revisión no válido.')
        current = type(self).objects.select_for_update().get(pk=self.pk)
        if current.status != self.Status.PENDING:
            raise ValidationError('Solo se pueden revisar solicitudes pendientes.')
        self.status = status
        self.reviewed_by = user
        self.admin_comment = comment
        self.reviewed_at = timezone.now()
        self.save(update_fields=['status', 'reviewed_by', 'admin_comment', 'reviewed_at', 'updated_at'])

# Create your models here.
