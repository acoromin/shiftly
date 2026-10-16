from .models import MonthlyHoursSummary


def monthly_summaries_for_company(company):
    if company is None:
        return MonthlyHoursSummary.objects.none()
    return MonthlyHoursSummary.objects.filter(company=company)
