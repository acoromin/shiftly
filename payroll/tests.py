from datetime import date, time
from decimal import Decimal
from importlib import import_module

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from companies.models import Company
from employees.models import EmployeeProfile
from incidents.models import Incident
from leaves.models import LeaveRequest
from scheduling.models import Shift
from timeclock.models import TimeClockEntry

from .models import MonthlyHoursSummary, PayrollDraft, PayrollDraftLine
from .selectors import monthly_summaries_for_company
from .services import calculate_employee_summary, generate_payroll_draft, recalculate_month


class MonthlySummaryTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa Base')
        self.user = User.objects.create_user(username='ana', password='secret')
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            company=self.company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
            weekly_contracted_hours=40,
        )

    def set_employee_company(self, employee=None, name='Empresa A'):
        employee = employee or self.employee
        company = Company.objects.create(name=name)
        employee.company = company
        employee.save(update_fields=['company'])
        return company

    def test_payroll_models_can_reference_company(self):
        company = self.set_employee_company()

        summary = MonthlyHoursSummary.objects.create(
            employee=self.employee,
            company=company,
            year=2026,
            month=6,
        )
        draft = PayrollDraft.objects.create(
            year=2026,
            month=6,
            company=company,
            generated_by=self.user,
        )
        line = PayrollDraftLine.objects.create(
            draft=draft,
            employee=self.employee,
            company=company,
        )

        self.assertEqual(summary.company, company)
        self.assertEqual(draft.company, company)
        self.assertEqual(line.company, company)

    def test_backfill_assigns_company_to_summary_draft_and_lines(self):
        company = self.set_employee_company()
        summary = MonthlyHoursSummary.objects.create(
            employee=self.employee,
            year=2026,
            month=6,
        )
        draft = PayrollDraft.objects.create(year=2026, month=6, generated_by=self.user)
        line = PayrollDraftLine.objects.create(draft=draft, employee=self.employee)
        migration = import_module('payroll.migrations.0004_backfill_payroll_company')

        migration.backfill_payroll_company(apps, None)
        summary.refresh_from_db()
        draft.refresh_from_db()
        line.refresh_from_db()

        self.assertEqual(summary.company, company)
        self.assertEqual(draft.company, company)
        self.assertEqual(line.company, company)

    def test_recalculate_month_filters_by_company_when_provided(self):
        company = self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        summaries = recalculate_month(2026, 6, company=company)

        self.assertEqual([summary.employee for summary in summaries], [self.employee])
        self.assertEqual(summaries[0].company, company)

    def test_recalculate_month_filters_out_other_company_employees_when_provided(self):
        company = self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        summaries = recalculate_month(2026, 6, company=company)

        self.assertEqual([summary.employee for summary in summaries], [self.employee])

    def test_generate_payroll_draft_filters_by_company(self):
        company = self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        draft = generate_payroll_draft(2026, 6, self.user, company=company)

        self.assertEqual(draft.company, company)
        self.assertEqual(draft.lines.count(), 1)
        line = draft.lines.get()
        self.assertEqual(line.employee, self.employee)
        self.assertEqual(line.company, company)

    def test_generate_payroll_draft_filters_out_other_company_employees(self):
        company = self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        draft = generate_payroll_draft(2026, 6, self.user, company=company)

        self.assertEqual(draft.lines.count(), 1)
        self.assertEqual(draft.lines.get().employee, self.employee)

    def test_monthly_summaries_for_company_only_returns_company_summaries(self):
        company = self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        summary = MonthlyHoursSummary.objects.create(
            employee=self.employee,
            company=company,
            year=2026,
            month=6,
        )
        MonthlyHoursSummary.objects.create(
            employee=other_employee,
            company=other_company,
            year=2026,
            month=6,
        )
        MonthlyHoursSummary.objects.create(
            employee=self.employee,
            year=2026,
            month=7,
        )

        self.assertEqual(list(monthly_summaries_for_company(company)), [summary])
        self.assertFalse(monthly_summaries_for_company(None).exists())

    def test_calculates_planned_and_clocked_hours(self):
        company = self.set_employee_company()
        Shift.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        TimeClockEntry.objects.create(
            employee=self.employee,
            company=self.employee.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 8, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        TimeClockEntry.objects.create(
            employee=self.employee,
            company=self.employee.company,
            entry_type=TimeClockEntry.EntryType.OUT,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 16, 30)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        summary = calculate_employee_summary(self.employee, 2026, 6)

        self.assertEqual(summary.planned_hours, Decimal('8.00'))
        self.assertEqual(summary.valid_clocked_hours, Decimal('8.50'))
        self.assertEqual(summary.detected_overtime_hours, Decimal('0.50'))
        self.assertEqual(summary.company, company)

    def test_calculate_employee_summary_filters_by_company_data(self):
        company = self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        Shift.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        TimeClockEntry.objects.create(
            employee=self.employee,
            company=company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 8, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        TimeClockEntry.objects.create(
            employee=self.employee,
            company=company,
            entry_type=TimeClockEntry.EntryType.OUT,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 16, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        TimeClockEntry.objects.create(
            employee=other_employee,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 24, 8, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )
        TimeClockEntry.objects.create(
            employee=other_employee,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.OUT,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 24, 12, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )

        summary = calculate_employee_summary(self.employee, 2026, 6, company=company)

        self.assertEqual(summary.planned_hours, Decimal('8.00'))
        self.assertEqual(summary.valid_clocked_hours, Decimal('8.00'))
        self.assertEqual(summary.company, company)

    def test_calculate_employee_summary_filters_out_other_company_data(self):
        company = self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        LeaveRequest.objects.create(
            employee=self.employee,
            company=company,
            request_type=LeaveRequest.RequestType.VACATION,
            status=LeaveRequest.Status.APPROVED,
            start_date=date(2026, 6, 3),
            end_date=date(2026, 6, 4),
        )
        LeaveRequest.objects.create(
            employee=self.employee,
            company=other_company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            status=LeaveRequest.Status.APPROVED,
            start_date=date(2026, 6, 5),
            end_date=date(2026, 6, 5),
        )
        Incident.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 6, 6),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Incidencia de empresa.',
            created_by=self.user,
        )
        Incident.objects.create(
            employee=self.employee,
            company=other_company,
            date=date(2026, 6, 7),
            incident_type=Incident.IncidentType.OTHER,
            description='Incidencia de otra empresa.',
            created_by=self.user,
        )

        summary = calculate_employee_summary(self.employee, 2026, 6, company=company)

        self.assertEqual(summary.approved_vacation_days, 2)
        self.assertEqual(summary.approved_day_off_days, 0)
        self.assertEqual(summary.pending_incidents_count, 1)

# Create your tests here.
