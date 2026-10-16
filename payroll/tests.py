from datetime import date, time
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.models import Company
from employees.models import EmployeeProfile
from incidents.models import Incident
from leaves.models import LeaveRequest
from scheduling.models import Shift
from timeclock.models import TimeClockEntry

from .models import MonthlyHoursSummary, PayrollDraft, PayrollDraftLine
from .selectors import monthly_summaries_for_company
from .services import calculate_clocked_hours, calculate_employee_summary, generate_payroll_draft, month_bounds, recalculate_month


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

    def test_payroll_services_require_company_and_do_not_create_data(self):
        _, _, start, end = month_bounds(2026, 6)
        calls = (
            lambda **kwargs: calculate_clocked_hours(self.employee, start, end, **kwargs),
            lambda **kwargs: calculate_employee_summary(self.employee, 2026, 6, **kwargs),
            lambda **kwargs: recalculate_month(2026, 6, **kwargs),
            lambda **kwargs: generate_payroll_draft(2026, 6, self.user, **kwargs),
        )
        for call in calls:
            for kwargs in ({}, {'company': None}, {'company': Company(name='Sin guardar')}):
                with self.subTest(call=call, kwargs=kwargs), self.assertRaises(ValueError):
                    call(**kwargs)
        self.assertFalse(MonthlyHoursSummary.objects.exists())
        self.assertFalse(PayrollDraft.objects.exists())
        self.assertFalse(PayrollDraftLine.objects.exists())

    def test_employee_calculations_reject_other_company_before_queries(self):
        other_company = Company.objects.create(name='Empresa B')
        _, _, start, end = month_bounds(2026, 6)
        with self.assertNumQueries(0), self.assertRaises(ValueError):
            calculate_employee_summary(self.employee, 2026, 6, company=other_company)
        with self.assertNumQueries(0), self.assertRaises(ValueError):
            calculate_clocked_hours(self.employee, start, end, company=other_company)

    def test_summary_does_not_include_legacy_data_from_other_company(self):
        other_company = Company.objects.create(name='Empresa B')
        # Deliberately inconsistent historical rows must never enter the calculation.
        LeaveRequest.objects.create(
            employee=self.employee, company=other_company,
            request_type=LeaveRequest.RequestType.VACATION, status=LeaveRequest.Status.APPROVED,
            start_date=date(2026, 6, 3), end_date=date(2026, 6, 4),
        )
        summary = calculate_employee_summary(self.employee, 2026, 6, company=self.company)
        self.assertEqual(summary.approved_vacation_days, 0)

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

    def test_monthly_summary_requires_company_in_model_and_database(self):
        summary = MonthlyHoursSummary(employee=self.employee, year=2026, month=6)
        with self.assertRaises(ValidationError) as context:
            summary.save()
        self.assertIn('company', context.exception.message_dict)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MonthlyHoursSummary.objects.bulk_create([summary])

    def test_monthly_summary_rejects_company_change_for_another_employee_company(self):
        summary = calculate_employee_summary(self.employee, 2026, 6, company=self.company)
        summary.company = Company.objects.create(name='Empresa B')
        with self.assertRaises(ValidationError):
            summary.save(update_fields=['company'])
        summary.refresh_from_db()
        self.assertEqual(summary.company, self.company)

    def test_monthly_summary_admin_exposes_company(self):
        model_admin = admin.site._registry[MonthlyHoursSummary]
        self.assertIn('company', model_admin.list_display)
        self.assertIn('company', model_admin.autocomplete_fields)

    def test_payroll_draft_requires_company_in_model_and_database(self):
        draft = PayrollDraft(year=2026, month=6, generated_by=self.user)
        with self.assertRaises(ValidationError) as context:
            draft.save()
        self.assertIn('company', context.exception.message_dict)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PayrollDraft.objects.bulk_create([draft])

    def test_payroll_draft_cannot_move_existing_lines_to_another_company(self):
        draft = generate_payroll_draft(2026, 6, self.user, company=self.company)
        draft.company = Company.objects.create(name='Empresa B')
        with self.assertRaises(ValidationError):
            draft.save(update_fields=['company'])
        draft.refresh_from_db()
        self.assertEqual(draft.company, self.company)

    def test_payroll_draft_admin_exposes_company(self):
        model_admin = admin.site._registry[PayrollDraft]
        self.assertIn('company', model_admin.list_display)
        self.assertIn('company', model_admin.autocomplete_fields)

    def test_payroll_line_requires_company_in_model_and_database(self):
        draft = PayrollDraft.objects.create(year=2026, month=6, company=self.company, generated_by=self.user)
        line = PayrollDraftLine(employee=self.employee, draft=draft)
        with self.assertRaises(ValidationError) as context:
            line.save()
        self.assertIn('company', context.exception.message_dict)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PayrollDraftLine.objects.bulk_create([line])

    def test_payroll_line_rejects_mismatched_employee_and_draft(self):
        other_company = Company.objects.create(name='Empresa B')
        draft = PayrollDraft.objects.create(year=2026, month=6, company=self.company, generated_by=self.user)
        other_draft = PayrollDraft.objects.create(year=2026, month=6, company=other_company, generated_by=self.user)
        for company, related_draft in ((other_company, draft), (self.company, other_draft)):
            with self.subTest(company=company):
                line = PayrollDraftLine(employee=self.employee, company=company, draft=related_draft)
                with self.assertRaises(ValidationError):
                    line.save()
        self.assertFalse(PayrollDraftLine.objects.exists())

    def test_payroll_line_rejects_company_change(self):
        draft = generate_payroll_draft(2026, 6, self.user, company=self.company)
        line = draft.lines.get()
        line.company = Company.objects.create(name='Empresa B')
        with self.assertRaises(ValidationError):
            line.save(update_fields=['company'])
        line.refresh_from_db()
        self.assertEqual(line.company, self.company)

    def test_admin_rejects_draft_company_change_with_inline_without_server_error(self):
        draft = generate_payroll_draft(2026, 6, self.user, company=self.company)
        line = draft.lines.get()
        other_company = Company.objects.create(name='Empresa B')
        self.user.is_staff = self.user.is_superuser = True
        self.user.save(update_fields=['is_staff', 'is_superuser'])
        self.client.force_login(self.user)
        response = self.client.post(reverse('admin:payroll_payrolldraft_change', args=[draft.pk]), {
            'year': 2026, 'month': 6, 'company': other_company.pk,
            'status': PayrollDraft.Status.DRAFT, 'generated_by': self.user.pk,
            'lines-TOTAL_FORMS': 1, 'lines-INITIAL_FORMS': 1,
            'lines-MIN_NUM_FORMS': 0, 'lines-MAX_NUM_FORMS': 1000,
            'lines-0-id': line.pk, 'lines-0-draft': draft.pk, '_save': 'Guardar',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La empresa del borrador debe coincidir')
        draft.refresh_from_db()
        line.refresh_from_db()
        self.assertEqual(draft.company, self.company)
        self.assertEqual(line.company, self.company)

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

        summary = calculate_employee_summary(self.employee, 2026, 6, company=company)

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
