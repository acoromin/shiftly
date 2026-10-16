from django.db.utils import OperationalError, ProgrammingError

from .models import BusinessConfig


def maintenance_status(request):
    try:
        config = BusinessConfig.get_solo()
    except (OperationalError, ProgrammingError):
        return {}
    return {
        'maintenance_active': config.is_maintenance_active(),
        'maintenance_config': config,
    }
