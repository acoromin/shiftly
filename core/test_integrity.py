from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.models import Company
from employees.models import EmployeeProfile
from incidents.models import Incident
from leaves.models import LeaveRequest
from payroll.models import MonthlyHoursSummary, PayrollDraft, PayrollDraftLine
from scheduling.models import Shift
from timeclock.models import TimeClockEntry


class OperationalIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name='Empresa A')
        cls.other_company = Company.objects.create(name='Empresa B')
        cls.user = User.objects.create_user(username='admin')
        cls.employee = EmployeeProfile.objects.create(
            user=cls.user, company=cls.company, full_name='Admin A',
            start_date=date(2026, 1, 1), role=EmployeeProfile.Role.ADMIN,
        )
        cls.peer = EmployeeProfile.objects.create(
            user=User.objects.create_user(username='peer'), company=cls.company,
            full_name='Empleado A', start_date=date(2026, 1, 1),
        )
        cls.foreign_user = User.objects.create_user(username='admin-b')
        EmployeeProfile.objects.create(
            user=cls.foreign_user, company=cls.other_company, full_name='Admin B',
            start_date=date(2026, 1, 1), role=EmployeeProfile.Role.ADMIN,
        )

    def incident(self, employee=None, **kwargs):
        return Incident.objects.create(
            employee=employee or self.employee, company=self.company, date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.OTHER, description='Revisar fichaje',
            created_by=self.user, **kwargs,
        )

    def leave(self, employee=None, **kwargs):
        return LeaveRequest.objects.create(
            employee=employee or self.employee, company=self.company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 1), **kwargs,
        )

    def test_incident_rejects_another_employees_shift_and_clock_on_create_and_update(self):
        shift = Shift.objects.create(
            employee=self.peer, company=self.company, date=date(2026, 7, 1),
            start_time=time(8), end_time=time(16),
        )
        clock = TimeClockEntry.objects.create(
            employee=self.peer, company=self.company, entry_type='in',
            timestamp=timezone.now(), created_by=self.user,
        )
        incident = self.incident()
        for field, value in (('shift', shift), ('timeclock_entry', clock)):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as context:
                    self.incident(**{field: value})
                self.assertIn(field, context.exception.message_dict)
                setattr(incident, field, value)
                with self.assertRaises(ValidationError):
                    incident.save(update_fields=[field])
                incident.refresh_from_db()
                self.assertIsNone(getattr(incident, field))

    def test_incident_accepts_own_shift_and_clock(self):
        shift = Shift.objects.create(
            employee=self.employee, company=self.company, date=date(2026, 7, 1),
            start_time=time(8), end_time=time(16),
        )
        clock = TimeClockEntry.objects.create(
            employee=self.employee, company=self.company, related_shift=shift,
            entry_type='in', timestamp=timezone.now(), created_by=self.user,
        )
        incident = self.incident(shift=shift, timeclock_entry=clock)
        self.assertEqual(incident.shift, shift)
        self.assertEqual(incident.timeclock_entry, clock)

    def test_foreign_reviewer_and_resolver_cannot_write(self):
        leave = self.leave()
        incident = self.incident()
        with self.assertRaises(ValidationError):
            leave.review(status=LeaveRequest.Status.APPROVED, user=self.foreign_user)
        with self.assertRaises(ValidationError):
            incident.resolve(status=Incident.Status.RESOLVED, user=self.foreign_user)
        leave.refresh_from_db()
        incident.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.PENDING)
        self.assertIsNone(leave.reviewed_by)
        self.assertEqual(incident.status, Incident.Status.PENDING)
        self.assertIsNone(incident.resolved_by)

    def test_stale_review_and_resolution_do_not_overwrite_completed_actions(self):
        leave = self.leave()
        incident = self.incident()
        stale_leave = LeaveRequest.objects.get(pk=leave.pk)
        stale_incident = Incident.objects.get(pk=incident.pk)
        leave.review(status=LeaveRequest.Status.APPROVED, user=self.user, comment='Primera revision')
        incident.resolve(status=Incident.Status.RESOLVED, user=self.user, comment='Primera resolucion')
        with self.assertRaises(ValidationError):
            stale_leave.review(status=LeaveRequest.Status.REJECTED, user=self.user)
        with self.assertRaises(ValidationError):
            stale_incident.resolve(status=Incident.Status.REJECTED, user=self.user)
        leave.refresh_from_db()
        incident.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(leave.admin_comment, 'Primera revision')
        self.assertEqual(incident.resolution_comment, 'Primera resolucion')

    def test_duplicate_posts_and_cancelled_request_return_errors_without_server_failure(self):
        leave = self.leave(status=LeaveRequest.Status.CANCELLED)
        incident = self.incident()
        incident.resolve(status=Incident.Status.RESOLVED, user=self.user)
        self.client.force_login(self.user)
        response = self.client.post(reverse('leaves:review', args=[leave.pk, 'approved']), {'admin_comment': 'Intento repetido'})
        self.assertRedirects(response, reverse('leaves:list'))
        response = self.client.post(reverse('incidents:resolve', args=[incident.pk, 'rejected']), {'resolution_comment': 'Intento repetido'})
        self.assertRedirects(response, reverse('incidents:list'))
        leave.refresh_from_db()
        incident.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.Status.CANCELLED)
        self.assertEqual(incident.status, Incident.Status.RESOLVED)

    def test_technical_superuser_without_profile_can_review_and_resolve(self):
        technician = User.objects.create_superuser(username='technician')
        leave = self.leave()
        incident = self.incident()
        leave.review(status=LeaveRequest.Status.APPROVED, user=technician)
        incident.resolve(status=Incident.Status.RESOLVED, user=technician)
        self.assertEqual(leave.reviewed_by, technician)
        self.assertEqual(incident.resolved_by, technician)

    def test_employee_company_can_change_before_operational_history(self):
        self.employee.company = self.other_company
        self.employee.save(update_fields=['company'])
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.company, self.other_company)

    def test_employee_company_cannot_change_with_each_kind_of_operational_history(self):
        draft = PayrollDraft.objects.create(year=2026, month=7, company=self.company, generated_by=self.user)
        factories = (
            lambda e: Shift.objects.create(employee=e, company=self.company, date=date(2026, 7, 1), start_time=time(8), end_time=time(16)),
            lambda e: TimeClockEntry.objects.create(employee=e, company=self.company, entry_type='in', timestamp=timezone.now(), created_by=self.user),
            lambda e: self.leave(employee=e),
            lambda e: self.incident(employee=e),
            lambda e: MonthlyHoursSummary.objects.create(employee=e, company=self.company, year=2026, month=7),
            lambda e: PayrollDraftLine.objects.create(employee=e, company=self.company, draft=draft),
        )
        for index, factory in enumerate(factories):
            employee = EmployeeProfile.objects.create(
                user=User.objects.create_user(username=f'worker-{index}'), company=self.company,
                full_name='Con historico', start_date=date(2026, 1, 1),
            )
            record = factory(employee)
            with self.subTest(model=type(record).__name__):
                employee.company = self.other_company
                with self.assertRaises(ValidationError):
                    employee.save(update_fields=['company'])
                employee.refresh_from_db()
                record.refresh_from_db()
                self.assertEqual(employee.company, self.company)
                self.assertEqual(record.company, self.company)

    def test_reviewer_history_also_prevents_company_changes(self):
        leave = self.leave(employee=self.peer)
        leave.review(status=LeaveRequest.Status.APPROVED, user=self.user)
        self.employee.company = self.other_company
        with self.assertRaises(ValidationError):
            self.employee.save(update_fields=['company'])
