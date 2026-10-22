import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MaxValueValidator
from django.db import models


class Company(models.Model):
    class BusinessType(models.TextChoices):
        BAR = 'bar', 'Bar'
        RESTAURANT = 'restaurant', 'Restaurante'
        CAFE = 'cafe', 'Cafeteria'
        RETAIL = 'retail', 'Comercio'
        HAIR_SALON = 'hair_salon', 'Peluqueria'
        BEAUTY_CENTER = 'beauty_center', 'Centro de estetica'
        MASSAGE_CENTER = 'massage_center', 'Centro de masajes'
        GYM = 'gym', 'Gimnasio'
        ACADEMY = 'academy', 'Academia'
        BAKERY = 'bakery', 'Panaderia'
        CLINIC = 'clinic', 'Clinica'
        OTHER = 'other', 'Otro'

    name = models.CharField('nombre', max_length=160)
    business_type = models.CharField(
        'tipo de negocio',
        max_length=40,
        choices=BusinessType.choices,
        default=BusinessType.OTHER,
    )
    contact_email = models.EmailField('correo de contacto', blank=True)
    phone = models.CharField('telefono', max_length=30, blank=True)
    tax_id = models.CharField('CIF/NIF', max_length=30, blank=True)
    is_active = models.BooleanField('activa', default=True)
    clock_tolerance_minutes = models.PositiveSmallIntegerField(
        'minutos de tolerancia', default=5, validators=[MaxValueValidator(32767)],
    )
    general_config = models.JSONField('configuracion general', default=dict, blank=True)
    created_at = models.DateTimeField('fecha de alta', auto_now_add=True)
    updated_at = models.DateTimeField('actualizada el', auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'empresa'
        verbose_name_plural = 'empresas'
        indexes = [
            models.Index(fields=['is_active', 'name']),
            models.Index(fields=['business_type']),
        ]

    def __str__(self):
        return self.name


class Workplace(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='workplaces',
        verbose_name='empresa',
    )
    name = models.CharField('nombre', max_length=160)
    address = models.CharField('direccion', max_length=240, blank=True)
    city = models.CharField('ciudad', max_length=120, blank=True)
    postal_code = models.CharField('codigo postal', max_length=20, blank=True)
    public_wifi_ip = models.GenericIPAddressField('IP publica permitida para fichaje', blank=True, null=True)
    qr_token_hash = models.CharField('token protegido del QR', max_length=256, blank=True)
    is_active = models.BooleanField('activo', default=True)
    regular_schedule = models.JSONField('horario habitual', default=dict, blank=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        ordering = ['company__name', 'name']
        verbose_name = 'centro de trabajo'
        verbose_name_plural = 'centros de trabajo'
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_workplace_name_per_company'),
        ]
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} · {self.company}'

    def set_qr_token(self, raw_token):
        self.qr_token_hash = make_password(raw_token)

    def check_qr_token(self, raw_token):
        if not raw_token or not self.qr_token_hash:
            return False
        return check_password(raw_token, self.qr_token_hash)

    @staticmethod
    def generate_qr_token():
        return secrets.token_urlsafe(48)


class JobPosition(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='job_positions',
        verbose_name='empresa',
    )
    name = models.CharField('nombre', max_length=120)
    description = models.TextField('descripcion', blank=True)
    color = models.CharField('color', max_length=20, blank=True)
    is_active = models.BooleanField('activo', default=True)
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado el', auto_now=True)

    class Meta:
        ordering = ['company__name', 'name']
        verbose_name = 'puesto'
        verbose_name_plural = 'puestos'
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_job_position_name_per_company'),
        ]
        indexes = [
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} · {self.company}'
