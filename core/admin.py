from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from .models import BusinessConfig


@admin.register(BusinessConfig)
class BusinessConfigAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'public_wifi_ip',
        'timezone',
        'clock_tolerance_minutes',
        'maintenance_enabled',
        'updated_at',
    )
    readonly_fields = ('updated_at', 'qr_configured')
    fields = (
        'name',
        'public_wifi_ip',
        'qr_configured',
        'timezone',
        'clock_tolerance_minutes',
        'maintenance_enabled',
        'maintenance_scheduled_start',
        'maintenance_scheduled_end',
        'maintenance_reason',
        'maintenance_message',
        'updated_by',
        'updated_at',
    )

    def has_add_permission(self, request):
        return not BusinessConfig.objects.exists()

    def qr_configured(self, obj):
        return 'Si' if obj and obj.qr_static_token_hash else 'No'
    qr_configured.short_description = 'QR configurado'

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/generar-token-qr/',
                self.admin_site.admin_view(self.generate_qr_token),
                name='core_businessconfig_generate_qr',
            ),
        ]
        return custom_urls + urls

    def generate_qr_token(self, request, object_id):
        config = BusinessConfig.objects.get(pk=object_id)
        token = BusinessConfig.generate_qr_token()
        config.set_qr_token(token)
        config.updated_by = request.user
        config.save()
        url = request.build_absolute_uri(reverse('timeclock:scan'))
        messages.warning(
            request,
            f'Token QR generado. Guarda esta URL para imprimir el QR: {url}?token={token}',
        )
        return HttpResponseRedirect(reverse('admin:core_businessconfig_change', args=[object_id]))

# Register your models here.
