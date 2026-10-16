from django.contrib import admin

from .models import TimeClockEntry


@admin.register(TimeClockEntry)
class TimeClockEntryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'employee', 'company', 'entry_type', 'status', 'detected_ip', 'created_by')
    list_filter = ('company', 'entry_type', 'status', 'timestamp')
    search_fields = ('employee__full_name', 'created_by__username', 'detected_ip', 'manual_reason')
    autocomplete_fields = ('employee', 'company', 'created_by', 'related_shift')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'

# Register your models here.
