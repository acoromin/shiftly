from django.core.exceptions import PermissionDenied

from .models import EmployeeProfile


def profile_for(user):
    return getattr(user, 'employee_profile', None)


def is_admin_profile(profile):
    return bool(
        profile and profile.is_active and profile.user.is_active
        and profile.role == EmployeeProfile.Role.ADMIN
    )


def is_company_admin_profile(profile):
    return is_admin_profile(profile) and bool(profile.company_id) and profile.company.is_active


def is_admin_without_company(profile):
    return is_admin_profile(profile) and not profile.company_id


def require_company_admin(user):
    profile = profile_for(user)
    if not is_company_admin_profile(profile):
        raise PermissionDenied
    return profile
