from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from audit.models import AuditLog
from employees.models import EmployeeProfile

from .forms import BusinessConfigForm
from .models import BusinessConfig


def _require_admin(request):
    profile = getattr(request.user, 'employee_profile', None)
    if not request.user.is_superuser and (
        not profile or profile.role != EmployeeProfile.Role.ADMIN
    ):
        raise PermissionDenied


def _maintenance_payload(config):
    return {
        'enabled': config.maintenance_enabled,
        'scheduled_start': (
            config.maintenance_scheduled_start.isoformat()
            if config.maintenance_scheduled_start else None
        ),
        'scheduled_end': (
            config.maintenance_scheduled_end.isoformat()
            if config.maintenance_scheduled_end else None
        ),
        'reason': config.maintenance_reason,
    }


@login_required
def settings(request):
    _require_admin(request)
    config = BusinessConfig.get_solo()
    old_payload = _maintenance_payload(config)

    if request.method == 'POST' and request.POST.get('action') == 'disable':
        config.maintenance_enabled = False
        config.maintenance_scheduled_start = None
        config.maintenance_scheduled_end = None
        config.updated_by = request.user
        config.save()
        AuditLog.objects.create(
            user=request.user,
            action=AuditLog.Action.MAINTENANCE_DISABLED,
            entity_type='BusinessConfig',
            entity_id=str(config.pk),
            old_value=old_payload,
            new_value=_maintenance_payload(config),
        )
        messages.success(request, 'Modo mantenimiento desactivado y programación eliminada.')
        return redirect('core:settings')

    form = BusinessConfigForm(request.POST or None, instance=config)
    if request.method == 'POST' and form.is_valid():
        config = form.save(commit=False)
        action = request.POST.get('action', 'save')
        if action == 'activate':
            config.maintenance_enabled = True
        config.updated_by = request.user
        config.save()

        new_payload = _maintenance_payload(config)
        if config.maintenance_enabled and not old_payload['enabled']:
            audit_action = AuditLog.Action.MAINTENANCE_ENABLED
        elif old_payload['enabled'] and not config.maintenance_enabled:
            audit_action = AuditLog.Action.MAINTENANCE_DISABLED
        else:
            audit_action = AuditLog.Action.MAINTENANCE_SCHEDULED
        AuditLog.objects.create(
            user=request.user,
            action=audit_action,
            entity_type='BusinessConfig',
            entity_id=str(config.pk),
            old_value=old_payload,
            new_value=new_payload,
        )

        if config.maintenance_scheduled_start:
            if config.maintenance_scheduled_start.weekday() == 0:
                messages.success(request, 'Mantenimiento programado para el lunes.')
            else:
                messages.warning(
                    request,
                    'Mantenimiento programado fuera del lunes. Se permite para emergencias.',
                )
        elif config.maintenance_enabled:
            messages.warning(request, 'Modo mantenimiento activado inmediatamente.')
        else:
            messages.success(request, 'Configuración guardada.')
        return redirect('core:settings')

    return render(
        request,
        'core/settings.html',
        {
            'form': form,
            'config': config,
            'maintenance_active_now': config.is_maintenance_active(),
        },
    )

# Create your views here.
