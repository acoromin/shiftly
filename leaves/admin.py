from django.contrib import admin

from .models import LeaveRequest


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'company', 'employee', 'request_type', 'status', 'reviewed_by')
    list_filter = ('company', 'request_type', 'status', 'start_date')
    search_fields = ('employee__full_name', 'worker_comment', 'admin_comment')
    autocomplete_fields = ('company', 'employee', 'reviewed_by')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at')
    date_hierarchy = 'start_date'

# Register your models here.
