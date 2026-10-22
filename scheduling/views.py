import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from employees.permissions import is_admin_without_company, is_company_admin_profile, profile_for

from .forms import ShiftForm
from .models import Shift
from .selectors import shifts_for_company, shifts_for_employee


def _profile_for(user):
    return profile_for(user)


def _can_manage_shifts(profile):
    return is_company_admin_profile(profile)


def _profile_company(profile):
    return profile.company if profile and profile.company_id else None


def _resolve_shift_context(employee, fallback_shift=None):
    company = employee.company if employee and employee.company_id else None
    workplace = None
    if company:
        if (
            fallback_shift
            and fallback_shift.workplace_id
            and fallback_shift.workplace.company_id == company.pk
        ):
            workplace = fallback_shift.workplace
        elif (
            employee.primary_workplace_id
            and employee.primary_workplace.company_id == company.pk
        ):
            workplace = employee.primary_workplace
    elif fallback_shift and fallback_shift.company_id:
        company = fallback_shift.company
        if (
            fallback_shift.workplace_id
            and fallback_shift.workplace.company_id == fallback_shift.company_id
        ):
            workplace = fallback_shift.workplace
    return company, workplace


def _apply_shift_context(shift, fallback_shift=None):
    shift.company, inferred_workplace = _resolve_shift_context(shift.employee, fallback_shift)
    if not shift.workplace_id:
        shift.workplace = inferred_workplace
    return shift


def _shifts_visible_to_profile(profile):
    if _can_manage_shifts(profile):
        return shifts_for_company(profile.company)
    if is_admin_without_company(profile):
        raise PermissionDenied
    return shifts_for_employee(profile)


def _week_start_from_request(request):
    raw = request.GET.get('week')
    if raw:
        try:
            selected = datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            selected = date.today()
    else:
        selected = date.today()
    return selected - timedelta(days=selected.weekday())


@login_required
def week(request):
    profile = _profile_for(request.user)
    if not profile:
        return render(request, 'scheduling/week.html', {'profile': None, 'days': []})

    week_start = _week_start_from_request(request)
    week_end = week_start + timedelta(days=6)
    shifts = _shifts_visible_to_profile(profile).select_related('employee').filter(
        is_active=True,
        date__range=(week_start, week_end),
    )

    shifts = list(shifts)
    shifts_by_day = []
    week_total_hours = Decimal('0.00')
    week_shift_count = len(shifts)
    workload = {}
    for offset in range(7):
        current = week_start + timedelta(days=offset)
        day_shifts = [shift for shift in shifts if shift.date == current]
        day_total_hours = sum(
            (Decimal(str(shift.planned_duration_hours)) for shift in day_shifts),
            Decimal('0.00'),
        )
        week_total_hours += day_total_hours
        shifts_by_day.append({
            'date': current,
            'shifts': day_shifts,
            'total_hours': day_total_hours,
        })
        for shift in day_shifts:
            workload.setdefault(shift.employee, Decimal('0.00'))
            workload[shift.employee] += Decimal(str(shift.planned_duration_hours))

    workload_warnings = [
        {
            'employee': employee,
            'hours': hours,
            'contracted': employee.weekly_contracted_hours,
        }
        for employee, hours in workload.items()
        if hours > employee.weekly_contracted_hours
    ]

    return render(
        request,
        'scheduling/week.html',
        {
            'profile': profile,
            'can_manage_shifts': _can_manage_shifts(profile),
            'week_start': week_start,
            'previous_week': week_start - timedelta(days=7),
            'next_week': week_start + timedelta(days=7),
            'days': shifts_by_day,
            'week_total_hours': week_total_hours,
            'week_shift_count': week_shift_count,
            'workload_warnings': workload_warnings,
        },
    )


@login_required
def create_shift(request):
    profile = _profile_for(request.user)
    if not _can_manage_shifts(profile):
        raise PermissionDenied

    form = ShiftForm(request.POST or None, company=_profile_company(profile), initial={'date': request.GET.get('fecha')})
    if request.method == 'POST' and form.is_valid():
        shift = form.save(commit=False)
        _apply_shift_context(shift)
        shift.created_by = request.user
        shift.modified_by = request.user
        shift.save()
        messages.success(request, 'Turno creado correctamente.')
        return redirect('scheduling:week')

    return render(request, 'scheduling/shift_form.html', {'form': form, 'creating': True})


@login_required
def edit_shift(request, pk):
    profile = _profile_for(request.user)
    if not _can_manage_shifts(profile):
        raise PermissionDenied
    shift = get_object_or_404(_shifts_visible_to_profile(profile), pk=pk, is_active=True)
    original_employee_id = shift.employee_id
    form = ShiftForm(request.POST or None, company=_profile_company(profile), instance=shift)
    if request.method == 'POST' and form.is_valid():
        shift = form.save(commit=False)
        fallback_shift = shift if shift.employee_id == original_employee_id else None
        _apply_shift_context(shift, fallback_shift=fallback_shift)
        shift.modified_by = request.user
        shift.save()
        messages.success(request, 'Turno actualizado correctamente.')
        return redirect(f"{reverse('scheduling:week')}?week={shift.date:%Y-%m-%d}")
    return render(
        request,
        'scheduling/shift_form.html',
        {'form': form, 'creating': False, 'shift': shift},
    )


@login_required
def duplicate_shift(request, pk):
    profile = _profile_for(request.user)
    if not _can_manage_shifts(profile) or request.method != 'POST':
        raise PermissionDenied
    original = get_object_or_404(_shifts_visible_to_profile(profile), pk=pk, is_active=True)
    duplicate = Shift(
        employee=original.employee,
        date=original.date + timedelta(days=7),
        start_time=original.start_time,
        end_time=original.end_time,
        planned_break_minutes=original.planned_break_minutes,
        position=original.position,
        notes=original.notes,
        workplace=original.workplace,
        created_by=request.user,
        modified_by=request.user,
    )
    _apply_shift_context(duplicate, fallback_shift=original)
    try:
        duplicate.save()
    except ValidationError:
        messages.error(request, 'No se pudo duplicar: el trabajador ya tiene un turno que se solapa.')
    else:
        messages.success(request, 'Turno duplicado en la semana siguiente.')
    return redirect(f"{reverse('scheduling:week')}?week={duplicate.date:%Y-%m-%d}")


@login_required
def cancel_shift(request, pk):
    profile = _profile_for(request.user)
    if not _can_manage_shifts(profile) or request.method != 'POST':
        raise PermissionDenied
    shift = get_object_or_404(_shifts_visible_to_profile(profile), pk=pk, is_active=True)
    shift.is_active = False
    shift.modified_by = request.user
    shift.save(update_fields=['is_active', 'modified_by', 'updated_at'])
    messages.success(request, 'Turno cancelado. Se conserva en el historial.')
    return redirect(f"{reverse('scheduling:week')}?week={shift.date:%Y-%m-%d}")


@login_required
def copy_previous_week(request):
    profile = _profile_for(request.user)
    if not _can_manage_shifts(profile) or request.method != 'POST':
        raise PermissionDenied
    target_start = _week_start_from_request(request)
    source_start = target_start - timedelta(days=7)
    source_end = source_start + timedelta(days=6)
    copied = 0
    skipped = 0
    shifts = _shifts_visible_to_profile(profile).select_related('employee', 'company', 'workplace').filter(
        is_active=True,
        date__range=(source_start, source_end),
    )
    for shift in shifts:
        new_shift = Shift(
            employee=shift.employee,
            date=shift.date + timedelta(days=7),
            start_time=shift.start_time,
            end_time=shift.end_time,
            planned_break_minutes=shift.planned_break_minutes,
            position=shift.position,
            notes=shift.notes,
            workplace=shift.workplace,
            created_by=request.user,
            modified_by=request.user,
        )
        _apply_shift_context(new_shift, fallback_shift=shift)
        try:
            new_shift.save()
        except ValidationError:
            skipped += 1
        else:
            copied += 1
    if copied:
        messages.success(request, f'Se han copiado {copied} turnos de la semana anterior.')
    if skipped:
        messages.warning(request, f'{skipped} turnos no se copiaron porque se solapaban.')
    return redirect(f"{reverse('scheduling:week')}?week={target_start:%Y-%m-%d}")


@login_required
def month(request):
    profile = _profile_for(request.user)
    if not profile:
        raise PermissionDenied
    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month_number = int(request.GET.get('month', today.month))
        selected = date(year, month_number, 1)
    except (TypeError, ValueError):
        selected = today.replace(day=1)
    previous_month = (selected - timedelta(days=1)).replace(day=1)
    next_month = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)
    calendar_weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(selected.year, selected.month)
    start, end = calendar_weeks[0][0], calendar_weeks[-1][-1]
    shifts = _shifts_visible_to_profile(profile).select_related('employee').filter(is_active=True, date__range=(start, end))
    shifts_by_date = {}
    for shift in shifts:
        shifts_by_date.setdefault(shift.date, []).append(shift)
    weeks = [
        [
            {
                'date': day,
                'in_month': day.month == selected.month,
                'shifts': shifts_by_date.get(day, []),
            }
            for day in week_days
        ]
        for week_days in calendar_weeks
    ]
    return render(
        request,
        'scheduling/month.html',
        {
            'profile': profile,
            'can_manage_shifts': _can_manage_shifts(profile),
            'selected': selected,
            'previous_month': previous_month,
            'next_month': next_month,
            'weeks': weeks,
        },
    )

# Create your views here.
