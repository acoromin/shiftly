from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from .permissions import is_technical_admin
from .throttling import LoginThrottleMixin


class TechnicalAdminAuthenticationForm(LoginThrottleMixin, AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError('Este acceso esta reservado a superusuarios tecnicos.', code='technical_admin_only')


class TechnicalAdminSite(AdminSite):
    """Global maintenance tools; customer operations use the company-scoped views."""

    login_form = TechnicalAdminAuthenticationForm

    def has_permission(self, request):
        return is_technical_admin(request.user)
