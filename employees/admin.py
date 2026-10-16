from django.contrib import admin

from .models import EmployeeProfile


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'company',
        'role',
        'primary_position',
        'contract_type',
        'weekly_contracted_hours',
        'is_active',
    )
    list_filter = ('company', 'role', 'primary_position', 'contract_type', 'is_active')
    search_fields = ('full_name', 'email', 'phone', 'dni_nie', 'user__username')
    autocomplete_fields = ('user', 'company')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Usuario y rol', {
            'fields': ('company', 'user', 'role', 'is_active'),
        }),
        ('Datos personales', {
            'fields': ('full_name', 'email', 'phone', 'dni_nie', 'color_label'),
        }),
        ('Datos laborales', {
            'fields': (
                'start_date',
                'end_date',
                'primary_position',
                'contract_type',
                'weekly_contracted_hours',
                'base_monthly_salary',
                'hourly_rate',
            ),
        }),
        ('Notas internas', {
            'fields': ('internal_notes',),
        }),
        ('Auditoría técnica', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

# Register your models here.
