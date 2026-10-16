from django.contrib import admin

from .models import MonthlyHoursSummary, PayrollDraft, PayrollDraftLine


@admin.register(MonthlyHoursSummary)
class MonthlyHoursSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'year',
        'month',
        'employee',
        'company',
        'planned_hours',
        'valid_clocked_hours',
        'detected_overtime_hours',
        'pending_incidents_count',
    )
    list_filter = ('company', 'year', 'month')
    autocomplete_fields = ('company', 'employee')
    search_fields = ('employee__full_name', 'observations')
    readonly_fields = ('calculated_at',)


class PayrollDraftLineInline(admin.TabularInline):
    model = PayrollDraftLine
    extra = 0
    readonly_fields = (
        'employee',
        'company',
        'contracted_hours',
        'planned_hours',
        'valid_clocked_hours',
        'pending_review_hours',
        'detected_overtime_hours',
        'approved_overtime_hours',
        'approved_vacation_days',
        'approved_day_off_days',
        'absence_days',
        'pending_incidents_count',
        'observations',
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PayrollDraft)
class PayrollDraftAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'company', 'status', 'generated_by', 'generated_at')
    list_filter = ('company', 'status', 'year', 'month')
    autocomplete_fields = ('company', 'generated_by')
    search_fields = ('generated_by__username', 'notes')
    readonly_fields = ('generated_at',)
    inlines = (PayrollDraftLineInline,)

# Register your models here.
