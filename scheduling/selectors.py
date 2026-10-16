from .models import Shift


def shifts_for_company(company):
    if company is None:
        return Shift.objects.none()
    return Shift.objects.filter(company=company)


def shifts_for_employee(employee):
    return Shift.objects.filter(employee=employee)
