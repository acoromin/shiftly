from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import render

from employees.models import EmployeeProfile

from .models import BusinessConfig


class MaintenanceModeMiddleware:
    EXEMPT_PATHS = {
        '/iniciar-sesion/',
        '/cerrar-sesion/',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/static/') or request.path in self.EXEMPT_PATHS:
            return self.get_response(request)

        try:
            config = BusinessConfig.get_solo()
        except (OperationalError, ProgrammingError):
            return self.get_response(request)

        if not config.is_maintenance_active():
            return self.get_response(request)

        user = request.user
        profile = getattr(user, 'employee_profile', None) if user.is_authenticated else None
        is_admin = bool(
            user.is_authenticated
            and (user.is_superuser or (profile and profile.role == EmployeeProfile.Role.ADMIN))
        )
        if is_admin or not user.is_authenticated:
            return self.get_response(request)

        return render(
            request,
            'maintenance.html',
            {'maintenance_config': config},
            status=503,
        )
