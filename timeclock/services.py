from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditLog
from core.models import BusinessConfig

from .models import TimeClockEntry


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


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


def resolve_timeclock_entry_context(employee, related_shift=None):
    if employee is None or not employee.company_id:
        raise ValidationError({'company': 'El empleado debe tener una empresa para registrar fichajes.'})
    company = employee.company
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


def attempt_clock(request, employee, token, related_shift=None):
    config = BusinessConfig.get_solo()
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    ensure_missing_clock_incident(employee)

    if not config.check_qr_token(token):
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
        )
        create_audit_log(
            request.user,
            AuditLog.Action.CLOCK_INVALID_QR,
            entry=entry,
            ip_address=ip_address,
            payload={'reason': 'invalid_qr'},
        )
        return False, 'QR no válido o caducado.', entry

    if not config.public_wifi_ip or ip_address != config.public_wifi_ip:
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
        )
        create_audit_log(
            request.user,
            AuditLog.Action.CLOCK_BLOCKED_IP,
            entry=entry,
            ip_address=ip_address,
            payload={'expected_ip': config.public_wifi_ip, 'detected_ip': ip_address},
        )
        return False, 'Debes estar conectado al WiFi del bar para fichar.', entry

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
    )
    action = AuditLog.Action.CLOCK_IN if entry_type == TimeClockEntry.EntryType.IN else AuditLog.Action.CLOCK_OUT
    create_audit_log(request.user, action, entry=entry, ip_address=ip_address)
    if entry_type == TimeClockEntry.EntryType.IN:
        return True, 'Entrada registrada correctamente.', entry
    return True, 'Salida registrada correctamente.', entry
