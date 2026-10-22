from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from audit.models import AuditLog
from employees.permissions import require_company_admin

from .forms import BusinessConfigForm, CompanySettingsForm
from .models import BusinessConfig
from .permissions import is_technical_admin


def _require_technical_admin(request):
    if not is_technical_admin(request.user):
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
    _require_technical_admin(request)
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
            messages.success(request, 'Mantenimiento global programado.')
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


@login_required
def company_settings(request):
    profile = require_company_admin(request.user)
    # The company is taken only from the authenticated profile, never from a submitted ID.
    form = CompanySettingsForm(request.POST or None, instance=profile.company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Configuración de tu empresa guardada.')
        return redirect('core:company-settings')
    return render(request, 'core/company_settings.html', {'form': form})
