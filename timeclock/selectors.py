from .models import TimeClockEntry


def timeclock_entries_for_company(company):
    if company is None:
        return TimeClockEntry.objects.none()
    return TimeClockEntry.objects.filter(company=company)


def timeclock_entries_for_employee(employee):
    return TimeClockEntry.objects.filter(employee=employee)
