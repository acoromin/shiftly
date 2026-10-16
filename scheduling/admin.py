from django.contrib import admin

from .models import Shift


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'company',
        'employee',
        'start_time',
        'end_time',
        'planned_break_minutes',
        'position',
        'is_active',
    )
    list_filter = ('company', 'date', 'position', 'is_active')
    search_fields = ('employee__full_name', 'employee__user__username', 'notes')
    autocomplete_fields = ('company', 'employee')
    readonly_fields = ('created_by', 'modified_by', 'created_at', 'updated_at')
    date_hierarchy = 'date'
    fieldsets = (
        ('Turno', {
            'fields': (
                'employee',
                'company',
                'date',
                'start_time',
                'end_time',
                'planned_break_minutes',
                'position',
                'is_active',
            ),
        }),
        ('Notas', {
            'fields': ('notes',),
        }),
        ('Auditoría técnica', {
            'fields': ('created_by', 'modified_by', 'created_at', 'updated_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)

# Register your models here.
