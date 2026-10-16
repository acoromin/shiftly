from django.contrib import admin

from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('date', 'company', 'employee', 'incident_type', 'status', 'created_by', 'resolved_by')
    list_filter = ('company', 'incident_type', 'status', 'date')
    search_fields = ('employee__full_name', 'description', 'resolution_comment')
    autocomplete_fields = ('company', 'employee', 'shift', 'timeclock_entry', 'created_by', 'resolved_by')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    date_hierarchy = 'date'

# Register your models here.
