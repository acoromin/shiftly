from django.contrib import admin

from .models import Company, JobPosition, Workplace


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_type', 'contact_email', 'phone', 'is_active', 'created_at')
    list_filter = ('business_type', 'is_active')
    search_fields = ('name', 'contact_email', 'phone', 'tax_id')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Empresa', {
            'fields': ('name', 'business_type', 'is_active'),
        }),
        ('Contacto', {
            'fields': ('contact_email', 'phone', 'tax_id'),
        }),
        ('Configuracion', {
            'fields': ('general_config',),
        }),
        ('Auditoria tecnica', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(Workplace)
class WorkplaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'city', 'public_wifi_ip', 'is_active')
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'company__name', 'address', 'city', 'postal_code', 'public_wifi_ip')
    autocomplete_fields = ('company',)
    readonly_fields = ('created_at', 'updated_at', 'qr_configured')
    fieldsets = (
        ('Centro de trabajo', {
            'fields': ('company', 'name', 'is_active'),
        }),
        ('Ubicacion', {
            'fields': ('address', 'city', 'postal_code'),
        }),
        ('Fichaje', {
            'fields': ('public_wifi_ip', 'qr_configured'),
        }),
        ('Horario habitual', {
            'fields': ('regular_schedule',),
        }),
        ('Auditoria tecnica', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def qr_configured(self, obj):
        return 'Si' if obj and obj.qr_token_hash else 'No'
    qr_configured.short_description = 'QR configurado'


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'color', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'company__name', 'description')
    autocomplete_fields = ('company',)
    readonly_fields = ('created_at', 'updated_at')
