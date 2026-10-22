from django.db.utils import OperationalError, ProgrammingError
from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.urls import reverse

from employees.permissions import is_company_admin_profile, profile_for

from .models import BusinessConfig
from .permissions import is_technical_admin


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

        user = request.user
        profile = profile_for(user) if user.is_authenticated else None
        technical_access = is_technical_admin(user)
        platform_route = (
            request.path == reverse('core:settings')
            or request.path.startswith(reverse('admin:index'))
        )
        if profile and not (technical_access and platform_route):
            if not profile.is_active or not profile.company_id or not profile.company.is_active:
                return HttpResponseForbidden('Tu perfil o empresa no tiene acceso activo.')

        try:
            config = BusinessConfig.objects.filter(pk=1).first()
        except (OperationalError, ProgrammingError):
            return self.get_response(request)

        if config is None or not config.is_maintenance_active():
            return self.get_response(request)

        is_admin = technical_access or is_company_admin_profile(profile)
        if is_admin or not user.is_authenticated:
            return self.get_response(request)

        return render(
            request,
            'maintenance.html',
            {'maintenance_config': config},
            status=503,
        )
