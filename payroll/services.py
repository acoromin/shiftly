import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from employees.selectors import active_employees_for_company
from employees.models import EmployeeProfile
from incidents.models import Incident
from leaves.models import LeaveRequest
from scheduling.models import Shift
from timeclock.models import TimeClockEntry

from .models import MonthlyHoursSummary, PayrollDraft, PayrollDraftLine


VALID_CLOCK_STATUSES = [
    TimeClockEntry.Status.VALID,
    TimeClockEntry.Status.MANUAL,
    TimeClockEntry.Status.CORRECTED,
]


def month_bounds(year, month):
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    start = timezone.make_aware(datetime.combine(first, time.min))
    end = timezone.make_aware(datetime.combine(last + timedelta(days=1), time.min))
    return first, last, start, end


def decimal_hours(seconds):
    return (Decimal(seconds) / Decimal(3600)).quantize(Decimal('0.01'))


def days_inclusive(start_date, end_date):
    return (end_date - start_date).days + 1


def calculate_clocked_hours(employee, start_dt, end_dt, company=None):
    entries = TimeClockEntry.objects.filter(
        employee=employee,
        status__in=VALID_CLOCK_STATUSES,
        timestamp__gte=start_dt,
        timestamp__lt=end_dt,
    )
    if company:
        entries = entries.filter(company=company)
    entries = list(entries.order_by('timestamp', 'id'))
    open_entry = None
    valid_seconds = 0
    incomplete_count = 0

    for entry in entries:
        if entry.entry_type == TimeClockEntry.EntryType.IN:
            if open_entry is not None:
                incomplete_count += 1
            open_entry = entry
        elif entry.entry_type == TimeClockEntry.EntryType.OUT:
            if open_entry is None:
                incomplete_count += 1
            else:
                valid_seconds += max((entry.timestamp - open_entry.timestamp).total_seconds(), 0)
                open_entry = None

    if open_entry is not None:
        incomplete_count += 1

    return decimal_hours(valid_seconds), incomplete_count


def calculate_employee_summary(employee, year, month, company=None):
    if company and employee.company_id != company.pk:
        return None
    first, last, start_dt, end_dt = month_bounds(year, month)
    summary_company = company or (employee.company if employee.company_id else None)
    shifts = Shift.objects.filter(employee=employee, is_active=True, date__range=(first, last))
    if company:
        shifts = shifts.filter(company=company)
    planned_hours = sum(
        (Decimal(str(shift.planned_duration_hours)) for shift in shifts),
        Decimal('0.00'),
    )
    valid_hours, incomplete_count = calculate_clocked_hours(employee, start_dt, end_dt, company=company)
    contracted_hours = (employee.weekly_contracted_hours * Decimal('52') / Decimal('12')).quantize(Decimal('0.01'))

    approved_vacations = LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
        request_type=LeaveRequest.RequestType.VACATION,
        start_date__lte=last,
        end_date__gte=first,
    )
    if company:
        approved_vacations = approved_vacations.filter(company=company)
    approved_days_off = LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
        request_type=LeaveRequest.RequestType.DAY_OFF,
        start_date__lte=last,
        end_date__gte=first,
    )
    if company:
        approved_days_off = approved_days_off.filter(company=company)
    absences = LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
        request_type__in=[
            LeaveRequest.RequestType.JUSTIFIED_ABSENCE,
            LeaveRequest.RequestType.MEDICAL_ABSENCE,
        ],
        start_date__lte=last,
        end_date__gte=first,
    )
    if company:
        absences = absences.filter(company=company)
    pending_incidents_query = Incident.objects.filter(
        employee=employee,
        status=Incident.Status.PENDING,
        date__range=(first, last),
    )
    if company:
        pending_incidents_query = pending_incidents_query.filter(company=company)
    pending_incidents = pending_incidents_query.count()
    detected_overtime = max(valid_hours - planned_hours, Decimal('0.00')).quantize(Decimal('0.01'))
    observations = []
    if incomplete_count:
        observations.append(f'{incomplete_count} fichaje(s) incompleto(s).')
    if pending_incidents:
        observations.append(f'{pending_incidents} incidencia(s) pendiente(s).')

    summary, _ = MonthlyHoursSummary.objects.update_or_create(
        employee=employee,
        year=year,
        month=month,
        defaults={
            'company': summary_company,
            'contracted_hours': contracted_hours,
            'planned_hours': planned_hours.quantize(Decimal('0.01')),
            'valid_clocked_hours': valid_hours,
            'pending_review_hours': Decimal(incomplete_count),
            'detected_overtime_hours': detected_overtime,
            'approved_overtime_hours': Decimal('0.00'),
            'approved_vacation_days': sum(days_inclusive(item.start_date, item.end_date) for item in approved_vacations),
            'approved_day_off_days': sum(days_inclusive(item.start_date, item.end_date) for item in approved_days_off),
            'absence_days': sum(days_inclusive(item.start_date, item.end_date) for item in absences),
            'pending_incidents_count': pending_incidents,
            'observations': ' '.join(observations),
        },
    )
    return summary


def recalculate_month(year, month, company=None):
    summaries = []
    if company:
        employees = active_employees_for_company(company).order_by('full_name')
    else:
        employees = EmployeeProfile.objects.filter(is_active=True).order_by('full_name')
    for employee in employees:
        summary = calculate_employee_summary(employee, year, month, company=company)
        if summary is not None:
            summaries.append(summary)
    return summaries


@transaction.atomic
def generate_payroll_draft(year, month, user, company=None):
    summaries = recalculate_month(year, month, company=company)
    draft = PayrollDraft.objects.create(year=year, month=month, company=company, generated_by=user)
    for summary in summaries:
        line_company = summary.company or summary.employee.company or draft.company
        PayrollDraftLine.objects.create(
            draft=draft,
            employee=summary.employee,
            company=line_company,
            contracted_hours=summary.contracted_hours,
            planned_hours=summary.planned_hours,
            valid_clocked_hours=summary.valid_clocked_hours,
            pending_review_hours=summary.pending_review_hours,
            detected_overtime_hours=summary.detected_overtime_hours,
            approved_overtime_hours=summary.approved_overtime_hours,
            approved_vacation_days=summary.approved_vacation_days,
            approved_day_off_days=summary.approved_day_off_days,
            absence_days=summary.absence_days,
            pending_incidents_count=summary.pending_incidents_count,
            observations=summary.observations,
        )
    return draft
