from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audit.models import AuditLog
from employees.models import EmployeeProfile
from employees.permissions import is_admin_without_company, is_company_admin_profile
from payroll.services import calculate_employee_summary

from .forms import CorrectTimeClockEntryForm, ManualTimeClockEntryForm
from .models import TimeClockEntry
from .selectors import timeclock_entries_for_company, timeclock_entries_for_employee
from .services import (
    apply_timeclock_entry_context,
    attempt_clock,
    create_audit_log,
    ensure_missing_clock_incident,
    get_client_ip,
    last_valid_entry,
    next_entry_type,
)


def _can_manage_timeclock(profile):
    return is_company_admin_profile(profile)


def _timeclock_entries_for_admin(profile):
    return timeclock_entries_for_company(profile.company)


@login_required
def scan(request):
    profile = getattr(request.user, 'employee_profile', None)
    token = request.GET.get('token') or request.POST.get('token')
    if not profile or not profile.is_active:
        messages.error(request, 'Tu usuario no está asociado a un empleado activo.')
        return redirect('dashboard:index')
    ensure_missing_clock_incident(profile)

    if request.method == 'POST':
        ok, message, _entry = attempt_clock(request, profile, token)
        if ok:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('timeclock:scan-result')

    last_entry = last_valid_entry(profile)
    entry_type = next_entry_type(profile)
    is_clocked_in = bool(
        last_entry
        and last_entry.entry_type == TimeClockEntry.EntryType.IN
        and entry_type == TimeClockEntry.EntryType.OUT
    )
    return render(
        request,
        'timeclock/scan.html',
        {
            'profile': profile,
            'token': token,
            'entry_type': entry_type,
            'last_entry': last_entry,
            'is_clocked_in': is_clocked_in,
            'entry_type_in': TimeClockEntry.EntryType.IN,
        },
    )


@login_required
def result(request):
    return render(request, 'timeclock/result.html')


@login_required
def history(request):
    profile = getattr(request.user, 'employee_profile', None)
    if not profile:
        entries = TimeClockEntry.objects.none()
        can_view_team = False
    else:
        can_view_team = profile.role == EmployeeProfile.Role.ADMIN
        if can_view_team:
            if is_admin_without_company(profile):
                raise PermissionDenied
            entries = timeclock_entries_for_company(profile.company)
        else:
            entries = timeclock_entries_for_employee(profile)
        entries = entries.select_related('employee', 'created_by').order_by('-timestamp')

    return render(
        request,
        'timeclock/history.html',
        {
            'entries': entries[:200],
            'can_view_team': can_view_team,
            'profile': profile,
        },
    )


@login_required
def hours(request):
    profile = getattr(request.user, 'employee_profile', None)
    if not profile or not profile.is_active:
        raise PermissionDenied
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year, month = today.year, today.month
    if month < 1 or month > 12:
        month = today.month
    summary = calculate_employee_summary(profile, year, month, company=profile.company)
    return render(
        request,
        'timeclock/hours.html',
        {'profile': profile, 'summary': summary, 'year': year, 'month': month},
    )


@login_required
def manual_create(request):
    profile = getattr(request.user, 'employee_profile', None)
    if not _can_manage_timeclock(profile):
        raise PermissionDenied

    company = profile.company if profile.company_id else None
    form = ManualTimeClockEntryForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        entry.status = TimeClockEntry.Status.MANUAL
        entry.created_by = request.user
        if timezone.is_naive(entry.timestamp):
            entry.timestamp = timezone.make_aware(entry.timestamp)
        apply_timeclock_entry_context(entry)
        entry.full_clean()
        entry.save()
        create_audit_log(
            request.user,
            AuditLog.Action.CLOCK_MANUAL,
            entry=entry,
            ip_address=get_client_ip(request),
            payload={'manual_reason': entry.manual_reason},
        )
        messages.success(request, 'Fichaje manual creado correctamente.')
        return redirect('timeclock:history')

    return render(request, 'timeclock/manual_form.html', {'form': form})


@login_required
def correct_entry(request, pk):
    profile = getattr(request.user, 'employee_profile', None)
    if not _can_manage_timeclock(profile):
        raise PermissionDenied
    entry = get_object_or_404(_timeclock_entries_for_admin(profile).select_related('employee'), pk=pk)
    old_value = {
        'entry_type': entry.entry_type,
        'timestamp': entry.timestamp.isoformat(),
        'status': entry.status,
        'manual_reason': entry.manual_reason,
    }
    form = CorrectTimeClockEntryForm(request.POST or None, instance=entry)
    if request.method == 'POST' and form.is_valid():
        corrected = form.save(commit=False)
        if timezone.is_naive(corrected.timestamp):
            corrected.timestamp = timezone.make_aware(corrected.timestamp)
        corrected.status = TimeClockEntry.Status.CORRECTED
        corrected.save()
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.CLOCK_CORRECTED,
            entity_type='TimeClockEntry',
            entity_id=str(corrected.pk),
            old_value=old_value,
            new_value={
                'entry_type': corrected.entry_type,
                'timestamp': corrected.timestamp.isoformat(),
                'status': corrected.status,
                'manual_reason': corrected.manual_reason,
            },
            ip_address=get_client_ip(request),
        )
        messages.success(request, 'Fichaje corregido y registrado en la auditoría.')
        return redirect('timeclock:history')
    return render(
        request,
        'timeclock/correct_form.html',
        {'form': form, 'entry': entry},
    )

# Create your views here.
