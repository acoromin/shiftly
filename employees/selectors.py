from .models import EmployeeProfile


def employees_for_company(company):
    if company is None:
        return EmployeeProfile.objects.none()
    return EmployeeProfile.objects.filter(company=company)


def active_employees_for_company(company):
    return employees_for_company(company).filter(is_active=True)
