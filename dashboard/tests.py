from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.models import Company
from core.models import BusinessConfig
from employees.models import EmployeeProfile
from incidents.models import Incident
from leaves.models import LeaveRequest
from scheduling.models import Shift
from timeclock.models import TimeClockEntry


class DashboardTests(TestCase):
    def test_admin_dashboard_shows_team_operational_data(self):
        company = Company.objects.create(name='Empresa A')
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        worker_user = User.objects.create_user(username='ana', password='secret')
        worker = EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        Shift.objects.create(
            employee=worker,
            company=company,
            date=timezone.localdate(),
            start_time=time(23, 0),
            end_time=time(23, 30),
        )

        self.client.force_login(admin_user)
        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Panel principal')
        self.assertContains(response, 'Ana Garcia')
        self.assertContains(response, '2 empleados activos')

    def test_worker_dashboard_only_shows_own_next_shift(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        user = User.objects.create_user(username='ana', password='secret')
        employee = EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        future_date = timezone.localdate() + timedelta(days=1)
        Shift.objects.create(
            employee=employee,
            company=company,
            date=future_date,
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        Shift.objects.create(
            employee=other,
            company=other_company,
            date=future_date,
            start_time=time(16, 0),
            end_time=time(23, 0),
        )

        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hola, Ana Garcia')
        self.assertContains(response, '08:00 - 16:00')
        self.assertNotContains(response, '16:00 - 23:00')
        self.assertNotContains(response, 'Luis Perez')

    def test_admin_dashboard_missing_clock_incident_saves_company(self):
        config = BusinessConfig.get_solo()
        config.clock_tolerance_minutes = 0
        config.save(update_fields=['clock_tolerance_minutes'])
        company = Company.objects.create(name='Empresa A')
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        worker_user = User.objects.create_user(username='ana', password='secret')
        worker = EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        Shift.objects.create(
            employee=worker,
            company=company,
            date=timezone.localdate(),
            start_time=time(0, 0),
            end_time=time(1, 0),
            created_by=admin_user,
        )

        self.client.force_login(admin_user)
        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        incident = Incident.objects.get(employee=worker, incident_type=Incident.IncidentType.MISSING_CLOCK_IN)
        self.assertEqual(incident.company, company)

    def test_admin_with_company_dashboard_only_uses_company_data(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        worker_user = User.objects.create_user(username='ana', password='secret')
        worker = EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        today = timezone.localdate()
        for employee, entry_company, hour in [
            (worker, company, 8),
            (other, other_company, 9),
        ]:
            Shift.objects.create(
                employee=employee,
                company=entry_company,
                date=today,
                start_time=time(hour, 0),
                end_time=time(hour + 1, 0),
                created_by=admin_user,
            )
            TimeClockEntry.objects.create(
                employee=employee,
                company=entry_company,
                entry_type=TimeClockEntry.EntryType.IN,
                timestamp=timezone.now() - timedelta(minutes=hour),
                status=TimeClockEntry.Status.VALID,
                created_by=employee.user,
            )
            TimeClockEntry.objects.create(
                employee=employee,
                company=entry_company,
                entry_type=TimeClockEntry.EntryType.IN,
                timestamp=timezone.now() - timedelta(days=1, minutes=hour),
                status=TimeClockEntry.Status.INVALID_QR,
                created_by=employee.user,
            )
            LeaveRequest.objects.create(
                employee=employee,
                company=entry_company,
                request_type=LeaveRequest.RequestType.VACATION,
                status=LeaveRequest.Status.PENDING,
                start_date=today,
                end_date=today,
            )
            Incident.objects.create(
                employee=employee,
                company=entry_company,
                date=today,
                incident_type=Incident.IncidentType.CLOCK_ERROR,
                description=f'Incidencia {employee.full_name}',
                created_by=employee.user,
            )

        self.client.force_login(admin_user)
        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_employee_count'], 2)
        self.assertEqual(response.context['pending_leaves'], 1)
        self.assertEqual(response.context['pending_incidents'], 1)
        self.assertEqual([shift.employee for shift in response.context['today_shifts']], [worker])
        self.assertEqual([entry.employee for entry in response.context['open_clock_entries']], [worker])
        self.assertTrue(all(entry.company == company for entry in response.context['recent_entries']))
        self.assertTrue(all(entry.company == company for entry in response.context['blocked_entries']))
