from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'user', 'entity_type', 'entity_id', 'ip_address')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'entity_type', 'entity_id', 'ip_address')
    readonly_fields = (
        'user',
        'action',
        'entity_type',
        'entity_id',
        'old_value',
        'new_value',
        'ip_address',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

# Register your models here.
