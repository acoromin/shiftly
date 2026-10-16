from .models import Incident


def incidents_for_company(company):
    if company is None:
        return Incident.objects.none()
    return Incident.objects.filter(company=company)


def incidents_for_employee(employee):
    return Incident.objects.filter(employee=employee)
