from django.contrib import admin

from .models import BusinessConfig


@admin.register(BusinessConfig)
class BusinessConfigAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'timezone',
        'maintenance_enabled',
        'updated_at',
    )
    readonly_fields = ('name', 'updated_at')
    fields = (
        'name',
        'timezone',
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

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

# Register your models here.
