import csv
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render

from employees.permissions import is_company_admin_profile
from payroll.services import generate_payroll_draft, recalculate_month


def _profile_for(user):
    return getattr(user, 'employee_profile', None)


def _can_view_reports(profile):
    return is_company_admin_profile(profile)


def _company_for_reports(profile):
    return profile.company


def _year_month_from_request(request):
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    if month < 1 or month > 12:
        month = today.month
    return year, month


@login_required
def monthly_summary(request):
    profile = _profile_for(request.user)
    if not _can_view_reports(profile):
        raise PermissionDenied
    year, month = _year_month_from_request(request)
    company = _company_for_reports(profile)
    summaries = recalculate_month(year, month, company=company)
    return render(
        request,
        'reports/monthly_summary.html',
        {'year': year, 'month': month, 'summaries': summaries},
    )


@login_required
def payroll_csv(request):
    profile = _profile_for(request.user)
    if not _can_view_reports(profile):
        raise PermissionDenied
    year, month = _year_month_from_request(request)
    company = _company_for_reports(profile)
    draft = generate_payroll_draft(year, month, request.user, company=company)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="xarlot-pre-nomina-{year}-{month:02d}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'empleado',
        'mes',
        'horas_contratadas',
        'horas_planificadas',
        'horas_fichadas_validas',
        'horas_pendientes_revision',
        'horas_extra_detectadas',
        'horas_extra_aprobadas',
        'vacaciones_aprobadas',
        'dias_libres_aprobados',
        'ausencias',
        'incidencias_pendientes',
        'observaciones',
    ])
    lines = draft.lines.select_related('employee')
    if company:
        lines = lines.filter(company=company)
    for line in lines:
        writer.writerow([
            line.employee.full_name,
            f'{month:02d}/{year}',
            line.contracted_hours,
            line.planned_hours,
            line.valid_clocked_hours,
            line.pending_review_hours,
            line.detected_overtime_hours,
            line.approved_overtime_hours,
            line.approved_vacation_days,
            line.approved_day_off_days,
            line.absence_days,
            line.pending_incidents_count,
            line.observations,
        ])
    return response

# Create your views here.
