from .models import LeaveRequest


def leave_requests_for_company(company):
    if company is None:
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.filter(company=company)


def leave_requests_for_employee(employee):
    return LeaveRequest.objects.filter(employee=employee)
