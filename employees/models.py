from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class EmployeeProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'administrador', 'Administrador'
        WORKER = 'trabajador', 'Trabajador'

    class Position(models.TextChoices):
        WAITER = 'camarero', 'Camarero'
        COOK = 'cocinero', 'Cocinero'

    class ContractType(models.TextChoices):
        FULL_TIME = 'full_time', 'Jornada completa'
        PART_TIME = 'part_time', 'Parcial'
        HOURLY = 'hourly', 'Por horas'
        REINFORCEMENT = 'reinforcement', 'Refuerzo'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='employee_profile',
        verbose_name='usuario',
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.PROTECT,
        related_name='employees',
        verbose_name='empresa',
    )
    primary_workplace = models.ForeignKey(
        'companies.Workplace',
        on_delete=models.PROTECT,
        related_name='primary_employees',
        verbose_name='centro principal',
        blank=True,
        null=True,
    )
    full_name = models.CharField('nombre completo', max_length=160)
    email = models.EmailField('correo electrónico', blank=True)
    phone = models.CharField('teléfono', max_length=30, blank=True)
    dni_nie = models.CharField('DNI/NIE', max_length=20, blank=True)
    start_date = models.DateField('fecha de alta')
    end_date = models.DateField('fecha de baja', blank=True, null=True)
    is_active = models.BooleanField('activo', default=True)
    role = models.CharField('tipo de usuario', max_length=20, choices=Role.choices, default=Role.WORKER)
    primary_position = models.CharField(
        'puesto de trabajo',
        max_length=20,
        choices=Position.choices,
        default=Position.WAITER,
    )
    contract_type = models.CharField(
        'tipo de contrato',
        max_length=20,
        choices=ContractType.choices,
        default=ContractType.FULL_TIME,
    )
    weekly_contracted_hours = models.DecimalField('horas semanales contratadas', max_digits=5, decimal_places=2, default=40)
    base_monthly_salary = models.DecimalField('salario mensual base', max_digits=10, decimal_places=2, blank=True, null=True)
    hourly_rate = models.DecimalField('precio por hora', max_digits=8, decimal_places=2, blank=True, null=True)
    internal_notes = models.TextField('notas internas', blank=True)
    color_label = models.CharField('color identificativo', max_length=20, blank=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'empleado'
        verbose_name_plural = 'empleados'

    def __str__(self):
        return self.full_name

    def clean(self):
        errors = {}
        if self.primary_workplace_id and not self.company_id:
            errors['company'] = 'Indica la empresa para asignar un centro principal.'
        elif (
            self.primary_workplace_id
            and self.company_id
            and self.primary_workplace.company_id != self.company_id
        ):
            errors['primary_workplace'] = 'El centro principal debe pertenecer a la misma empresa.'
        if errors:
            raise ValidationError(errors)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_worker(self):
        return self.role == self.Role.WORKER

# Create your models here.
