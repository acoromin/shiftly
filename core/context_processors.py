from django.db.utils import OperationalError, ProgrammingError
from employees.permissions import is_company_admin_profile, profile_for

from .models import BusinessConfig
from .permissions import is_technical_admin


def maintenance_status(request):
    permissions = {
        'can_manage_platform': is_technical_admin(request.user),
        'can_manage_company': is_company_admin_profile(profile_for(request.user)),
    }
    try:
        config = BusinessConfig.objects.filter(pk=1).first()
    except (OperationalError, ProgrammingError):
        return permissions
    return {
        **permissions,
        'maintenance_active': config is not None and config.is_maintenance_active(),
        'maintenance_config': config,
    }
