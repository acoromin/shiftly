from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils import timezone

from employees.models import EmployeeProfile
from employees.permissions import is_admin_without_company, is_company_admin_profile
from employees.selectors import active_employees_for_company
from incidents.models import Incident
from incidents.selectors import incidents_for_company
from leaves.models import LeaveRequest
from leaves.selectors import leave_requests_for_company
from payroll.services import calculate_employee_summary
from scheduling.models import Shift
from scheduling.selectors import shifts_for_company
from timeclock.models import TimeClockEntry
from timeclock.selectors import timeclock_entries_for_company
from timeclock.services import employees_with_open_clock_entries, ensure_missing_clock_incident, last_valid_entry


@login_required
def index(request):
    profile = getattr(request.user, 'employee_profile', None)
    role = profile.role if profile else 'unassigned'
    if is_admin_without_company(profile):
        raise PermissionDenied
    pending_leaves = 0
    pending_incidents = 0
    today = timezone.localdate()
    can_view_team = is_company_admin_profile(profile)
    today_shifts = Shift.objects.none()
    open_clock_entries = []
    recent_entries = TimeClockEntry.objects.none()
    blocked_entries = TimeClockEntry.objects.none()
    active_employee_count = 0
    missing_clock_ins = []
    next_shift = None
    current_entry = None
    is_clocked_in = False
    month_summary = None
    own_pending_leaves = 0
    own_open_incidents = 0

    if profile and can_view_team:
        company = profile.company
        active_employees = active_employees_for_company(company)
        leave_requests = leave_requests_for_company(company)
        incidents = incidents_for_company(company)
        shifts = shifts_for_company(company)
        entries = timeclock_entries_for_company(company)

        active_employee_count = active_employees.count()
        pending_leaves = leave_requests.filter(status=LeaveRequest.Status.PENDING).count()
        pending_incidents = incidents.filter(status=Incident.Status.PENDING).count()
        today_shifts = shifts.select_related('employee').filter(is_active=True, date=today)[:12]
        open_clock_entries = employees_with_open_clock_entries(active_employees)
        open_clock_entries = [entry for entry in open_clock_entries if entry.company_id == company.pk]
        recent_entries = entries.select_related('employee', 'created_by').order_by('-timestamp')[:8]
        blocked_entries = entries.select_related('employee').filter(
            status__in=[TimeClockEntry.Status.BLOCKED_IP, TimeClockEntry.Status.INVALID_QR],
            timestamp__gte=timezone.now() - timedelta(days=7),
        ).order_by('-timestamp')[:8]
        now = timezone.localtime()
        tolerance = timedelta(minutes=company.clock_tolerance_minutes)
        approved_absence_ids = leave_requests.filter(
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=today,
            end_date__gte=today,
        ).values_list('employee_id', flat=True)
        today_entries = entries.filter(
            timestamp__date=today,
            entry_type=TimeClockEntry.EntryType.IN,
            status__in=[
                TimeClockEntry.Status.VALID,
                TimeClockEntry.Status.MANUAL,
                TimeClockEntry.Status.CORRECTED,
            ],
        ).values_list('employee_id', flat=True)
        candidate_shifts = shifts.select_related('employee', 'created_by').filter(
            is_active=True,
            date=today,
            start_time__lte=now.time(),
        ).exclude(employee_id__in=today_entries).exclude(employee_id__in=approved_absence_ids)
        for shift in candidate_shifts:
            shift_start = timezone.make_aware(datetime.combine(today, shift.start_time))
            if now < shift_start + tolerance:
                continue
            Incident.objects.get_or_create(
                employee=shift.employee,
                shift=shift,
                incident_type=Incident.IncidentType.MISSING_CLOCK_IN,
                defaults={
                    'company': shift.company,
                    'date': today,
                    'description': 'El turno ha comenzado y no consta fichaje de entrada.',
                    'created_by': shift.created_by or request.user,
                },
            )
            missing_clock_ins.append(shift)
            if len(missing_clock_ins) == 8:
                break
    elif profile and role == EmployeeProfile.Role.WORKER:
        ensure_missing_clock_incident(profile)
        today_shifts = Shift.objects.filter(employee=profile, is_active=True, date=today)
        recent_entries = TimeClockEntry.objects.filter(employee=profile).order_by('-timestamp')[:6]
        next_shift = Shift.objects.filter(
            employee=profile,
            is_active=True,
            date__gte=today,
        ).order_by('date', 'start_time').first()
        current_entry = last_valid_entry(profile)
        is_clocked_in = bool(
            current_entry
            and current_entry.entry_type == TimeClockEntry.EntryType.IN
            and timezone.now() - current_entry.timestamp <= timedelta(hours=18)
        )
        month_summary = calculate_employee_summary(profile, today.year, today.month, company=profile.company)
        own_pending_leaves = LeaveRequest.objects.filter(
            employee=profile,
            status=LeaveRequest.Status.PENDING,
        ).count()
        own_open_incidents = Incident.objects.filter(
            employee=profile,
            status=Incident.Status.PENDING,
        ).count()

    return render(
        request,
        'dashboard/index.html',
        {
            'profile': profile,
            'role': role,
            'pending_leaves': pending_leaves,
            'pending_incidents': pending_incidents,
            'today': today,
            'today_shifts': today_shifts,
            'open_clock_entries': open_clock_entries,
            'recent_entries': recent_entries,
            'blocked_entries': blocked_entries,
            'active_employee_count': active_employee_count,
            'missing_clock_ins': missing_clock_ins,
            'next_shift': next_shift,
            'current_entry': current_entry,
            'is_clocked_in': is_clocked_in,
            'month_summary': month_summary,
            'own_pending_leaves': own_pending_leaves,
            'own_open_incidents': own_open_incidents,
        },
    )

# Create your views here.
