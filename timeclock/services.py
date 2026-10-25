from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditLog
from companies.models import Workplace
from core.network import get_client_ip
from core.throttling import consume_attempt
from scheduling.models import Shift

from .models import TimeClockEntry


def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')[:1000]


def last_valid_entry(employee):
    return (
        TimeClockEntry.objects
        .filter(
            employee=employee,
            status__in=[
                TimeClockEntry.Status.VALID,
                TimeClockEntry.Status.MANUAL,
                TimeClockEntry.Status.CORRECTED,
            ],
        )
        .order_by('-timestamp')
        .first()
    )


def employees_with_open_clock_entries(employee_queryset=None):
    if employee_queryset is None:
        raise ValueError('Indica el queryset de empleados autorizado para consultar fichajes abiertos.')
    open_entries = []
    for employee in employee_queryset:
        entry = last_valid_entry(employee)
        if (
            entry
            and entry.entry_type == TimeClockEntry.EntryType.IN
            and timezone.now() - entry.timestamp <= timedelta(hours=18)
        ):
            open_entries.append(entry)
        elif entry and entry.entry_type == TimeClockEntry.EntryType.IN:
            ensure_missing_clock_incident(employee)
    return open_entries


def next_entry_type(employee):
    last_entry = last_valid_entry(employee)
    if not last_entry or last_entry.entry_type == TimeClockEntry.EntryType.OUT:
        return TimeClockEntry.EntryType.IN
    if timezone.now() - last_entry.timestamp > timedelta(hours=18):
        return TimeClockEntry.EntryType.IN
    return TimeClockEntry.EntryType.OUT


def current_shift_for_employee(employee, at=None):
    at = timezone.localtime(at or timezone.now()).replace(tzinfo=None)
    candidates = Shift.objects.filter(
        employee=employee, company=employee.company, is_active=True,
        date__in=[at.date(), (at - timedelta(days=1)).date()],
    ).select_related('workplace')
    return next((shift for shift in candidates if shift.start_datetime <= at < shift.end_datetime), None)


def resolve_timeclock_entry_context(employee, related_shift=None):
    if employee is None or not employee.company_id:
        raise ValidationError({'company': 'El empleado debe tener una empresa para registrar fichajes.'})
    company = employee.company
    if related_shift and (related_shift.employee_id != employee.pk or related_shift.company_id != company.pk):
        raise ValidationError({'related_shift': 'El turno debe pertenecer al empleado y a su empresa.'})
    if related_shift and related_shift.workplace_id and related_shift.workplace.company_id != company.pk:
        raise ValidationError({'related_shift': 'El centro del turno debe pertenecer a la empresa del empleado.'})
    workplace = None
    if company:
        if (
            related_shift
            and related_shift.workplace_id
            and related_shift.workplace.company_id == company.pk
        ):
            workplace = related_shift.workplace
        elif (
            employee.primary_workplace_id
            and employee.primary_workplace.company_id == company.pk
        ):
            workplace = employee.primary_workplace
    return {'company': company, 'workplace': workplace}


def apply_timeclock_entry_context(entry, related_shift=None):
    context = resolve_timeclock_entry_context(entry.employee, related_shift or entry.related_shift)
    entry.company = context['company']
    if not entry.workplace_id:
        entry.workplace = context['workplace']
    return entry


def create_timeclock_entry(
    employee,
    *,
    entry_type,
    timestamp,
    detected_ip,
    user_agent,
    qr_token_label,
    status,
    created_by,
    related_shift=None,
    workplace=None,
):
    entry = TimeClockEntry(
        employee=employee,
        related_shift=related_shift,
        entry_type=entry_type,
        timestamp=timestamp,
        detected_ip=detected_ip,
        user_agent=user_agent,
        qr_token_label=qr_token_label,
        status=status,
        created_by=created_by,
    )
    apply_timeclock_entry_context(entry, related_shift=related_shift)
    if workplace is not None:
        entry.workplace = workplace
    entry.save()
    return entry


def ensure_missing_clock_incident(employee):
    last_entry = last_valid_entry(employee)
    if (
        not last_entry
        or last_entry.entry_type != TimeClockEntry.EntryType.IN
        or timezone.now() - last_entry.timestamp <= timedelta(hours=18)
    ):
        return None
    from incidents.models import Incident

    company = last_entry.company if last_entry.company_id else employee.company
    incident, _created = Incident.objects.get_or_create(
        employee=employee,
        timeclock_entry=last_entry,
        incident_type=Incident.IncidentType.MISSING_CLOCK_OUT,
        defaults={
            'company': company,
            'date': timezone.localtime(last_entry.timestamp).date(),
            'description': 'Se detectó una entrada antigua sin fichaje de salida.',
            'created_by': last_entry.created_by,
        },
    )
    return incident


def create_audit_log(user, action, entry=None, ip_address=None, payload=None):
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        entity_type='TimeClockEntry' if entry else '',
        entity_id=str(entry.pk) if entry else '',
        new_value=payload,
        ip_address=ip_address,
    )


def attempt_clock(request, employee, token, related_shift=None, public_id=None):
    if related_shift is None and employee is not None and employee.company_id:
        related_shift = current_shift_for_employee(employee)
    context = resolve_timeclock_entry_context(employee, related_shift)
    if not consume_attempt('clock', str(employee.pk), limit=20, window_seconds=60):
        return False, 'Demasiados intentos de fichaje. Espera un minuto.', None
    workplaces = Workplace.objects.filter(company=context['company'], is_active=True)
    shift_workplace = related_shift.workplace if related_shift and related_shift.workplace_id else None
    matched_workplace = None
    if token and len(token) <= 256 and public_id:
        try:
            public_uuid = UUID(str(public_id))
        except (ValueError, AttributeError):
            public_uuid = None
        if public_uuid:
            candidate = workplaces.filter(qr_public_id=public_uuid).first()
            if candidate and (not shift_workplace or candidate.pk == shift_workplace.pk):
                matched_workplace = candidate if candidate.check_qr_token(token) else None
    elif token and len(token) <= 256 and settings.CLOCK_ALLOW_LEGACY_QR:
        if shift_workplace:
            matched_workplace = shift_workplace if shift_workplace.is_active and shift_workplace.check_qr_token(token) else None
        else:
            matches = [place for place in workplaces if place.check_qr_token(token)]
            matched_workplace = matches[0] if len(matches) == 1 else None
    workplace = shift_workplace or matched_workplace
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    ensure_missing_clock_incident(employee)

    if not matched_workplace:
        attempted_workplace = shift_workplace or context['workplace']
        if attempted_workplace is None:
            create_audit_log(request.user, AuditLog.Action.CLOCK_INVALID_QR, ip_address=ip_address,
                             payload={'reason': 'invalid_qr', 'employee_id': employee.pk})
            return False, 'QR no válido o caducado.', None
        entry = create_timeclock_entry(
            employee=employee,
            entry_type=next_entry_type(employee),
            timestamp=timezone.now(),
            detected_ip=ip_address,
            user_agent=user_agent,
            qr_token_label='static',
            status=TimeClockEntry.Status.INVALID_QR,
            created_by=request.user,
            related_shift=related_shift,
            workplace=attempted_workplace,
        )
        create_audit_log(
            request.user,
            AuditLog.Action.CLOCK_INVALID_QR,
            entry=entry,
            ip_address=ip_address,
            payload={'reason': 'invalid_qr'},
        )
        return False, 'QR no válido o caducado.', entry

    if not workplace.public_wifi_ip or ip_address != workplace.public_wifi_ip:
        entry = create_timeclock_entry(
            employee=employee,
            entry_type=next_entry_type(employee),
            timestamp=timezone.now(),
            detected_ip=ip_address,
            user_agent=user_agent,
            qr_token_label='static',
            status=TimeClockEntry.Status.BLOCKED_IP,
            created_by=request.user,
            related_shift=related_shift,
            workplace=workplace,
        )
        create_audit_log(
            request.user,
            AuditLog.Action.CLOCK_BLOCKED_IP,
            entry=entry,
            ip_address=ip_address,
            payload={'expected_ip': workplace.public_wifi_ip, 'detected_ip': ip_address},
        )
        return False, 'Debes estar conectado al WiFi del centro para fichar.', entry

    last_entry = last_valid_entry(employee)
    if last_entry and timezone.now() - last_entry.timestamp < timedelta(seconds=60):
        return False, 'Espera un minuto antes de volver a fichar.', last_entry

    entry_type = next_entry_type(employee)
    entry = create_timeclock_entry(
        employee=employee,
        entry_type=entry_type,
        timestamp=timezone.now(),
        detected_ip=ip_address,
        user_agent=user_agent,
        qr_token_label='static',
        status=TimeClockEntry.Status.VALID,
        created_by=request.user,
        related_shift=related_shift,
        workplace=workplace,
    )
    action = AuditLog.Action.CLOCK_IN if entry_type == TimeClockEntry.EntryType.IN else AuditLog.Action.CLOCK_OUT
    create_audit_log(request.user, action, entry=entry, ip_address=ip_address)
    if entry_type == TimeClockEntry.EntryType.IN:
        return True, 'Entrada registrada correctamente.', entry
    return True, 'Salida registrada correctamente.', entry
