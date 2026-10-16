from datetime import date, time

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from companies.models import Company
from employees.models import EmployeeProfile
from scheduling.models import Shift
from timeclock.models import TimeClockEntry

from .models import Incident
from .selectors import incidents_for_company, incidents_for_employee


class IncidentTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa Base')
        self.user = User.objects.create_user(username='ana', password='secret')
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            company=self.company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

    def set_employee_company(self, employee=None, name='Empresa A'):
        employee = employee or self.employee
        company = Company.objects.create(name=name)
        employee.company = company
        employee.save(update_fields=['company'])
        return company

    def test_incident_can_reference_company(self):
        company = self.set_employee_company()

        incident = Incident.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )

        self.assertEqual(incident.company, company)

    def test_incident_requires_company(self):
        incident = Incident(
            employee=self.employee,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            incident.full_clean()

        self.assertIn('company', context.exception.message_dict)

    def test_incident_employee_must_belong_to_incident_company(self):
        self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        incident = Incident(
            employee=self.employee,
            company=other_company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            incident.full_clean()

        self.assertIn('employee', context.exception.message_dict)

    def test_incident_shift_must_belong_to_incident_company(self):
        company = self.set_employee_company(name='Empresa A')
        other_user = User.objects.create_user(username='luis', password='secret')
        other_company = Company.objects.create(name='Empresa B')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=other_employee,
            company=other_company,
            date=date(2026, 7, 1),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        incident = Incident(
            employee=self.employee,
            company=company,
            shift=shift,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            incident.full_clean()

        self.assertIn('shift', context.exception.message_dict)

    def test_incident_timeclock_entry_must_belong_to_incident_company(self):
        company = self.set_employee_company(name='Empresa A')
        other_user = User.objects.create_user(username='luis', password='secret')
        other_company = Company.objects.create(name='Empresa B')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        entry = TimeClockEntry.objects.create(
            employee=other_employee,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )
        incident = Incident(
            employee=self.employee,
            company=company,
            timeclock_entry=entry,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            incident.full_clean()

        self.assertIn('timeclock_entry', context.exception.message_dict)

    def test_incidents_for_company_only_returns_company_incidents(self):
        company = self.set_employee_company()
        other_user = User.objects.create_user(username='luis', password='secret')
        other_company = Company.objects.create(name='Empresa B')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        incident = Incident.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )
        Incident.objects.create(
            employee=other_employee,
            company=other_company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.OTHER,
            description='Texto de otra empresa.',
            created_by=other_user,
        )

        self.assertEqual(list(incidents_for_company(company)), [incident])
        self.assertFalse(incidents_for_company(None).exists())

    def test_django_admin_exposes_company(self):
        model_admin = admin.site._registry[Incident]

        self.assertIn('company', model_admin.list_display)
        self.assertIn('company', model_admin.list_filter)
        self.assertIn('company', model_admin.autocomplete_fields)

    def test_incidents_for_employee_only_returns_employee_incidents(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        incident = Incident.objects.create(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )
        Incident.objects.create(
            employee=other,
            company=other.company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.OTHER,
            description='Texto de otra persona.',
            created_by=other_user,
        )

        self.assertEqual(list(incidents_for_employee(self.employee)), [incident])

    def test_worker_only_sees_own_incidents(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        Incident.objects.create(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )
        Incident.objects.create(
            employee=other,
            company=other.company,
            date=date(2026, 8, 1),
            incident_type=Incident.IncidentType.OTHER,
            description='Texto de otra persona.',
            created_by=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('incidents:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mi fichaje no aparece.')
        self.assertNotContains(response, 'Texto de otra persona.')

    def test_admin_with_company_only_sees_company_incidents(self):
        company = self.set_employee_company()
        other_company = Company.objects.create(name='Empresa B')
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        Incident.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Incidencia empresa A.',
            created_by=self.user,
        )
        Incident.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.OTHER,
            description='Incidencia empresa B.',
            created_by=other_user,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('incidents:list'))

        self.assertContains(response, 'Incidencia empresa A.')
        self.assertNotContains(response, 'Incidencia empresa B.')

    def test_user_without_profile_incidents_list_is_empty(self):
        unassigned_user = User.objects.create_user(username='sinperfil', password='secret')
        Incident.objects.create(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Incidencia propia.',
            created_by=self.user,
        )

        self.client.force_login(unassigned_user)
        response = self.client.get(reverse('incidents:list'))

        self.assertContains(response, 'No hay incidencias.')
        self.assertNotContains(response, 'Incidencia propia.')

    def test_worker_can_create_incident(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('incidents:create'), {
            'date': '2026-07-01',
            'incident_type': Incident.IncidentType.CLOCK_ERROR,
            'description': 'No aparece mi entrada.',
        })

        self.assertRedirects(response, reverse('incidents:list'))
        self.assertTrue(Incident.objects.filter(employee=self.employee).exists())

    def test_worker_create_incident_saves_company(self):
        company = self.set_employee_company()
        self.client.force_login(self.user)

        response = self.client.post(reverse('incidents:create'), {
            'date': '2026-07-01',
            'incident_type': Incident.IncidentType.CLOCK_ERROR,
            'description': 'No aparece mi entrada.',
        })

        self.assertRedirects(response, reverse('incidents:list'))
        incident = Incident.objects.get(employee=self.employee)
        self.assertEqual(incident.company, company)

    def test_worker_cannot_resolve_incident(self):
        incident = Incident.objects.create(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('incidents:resolve', args=[incident.pk, 'resolved']))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_resolve_incident(self):
        company = self.set_employee_company()
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        incident = Incident.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('incidents:resolve', args=[incident.pk, Incident.Status.RESOLVED]), {
            'resolution_comment': 'Resuelto.',
        })

        self.assertRedirects(response, reverse('incidents:list'))
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.RESOLVED)

    def test_admin_with_company_can_resolve_company_incident(self):
        company = self.set_employee_company()
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        incident = Incident.objects.create(
            employee=self.employee,
            company=company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.CLOCK_ERROR,
            description='Mi fichaje no aparece.',
            created_by=self.user,
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('incidents:resolve', args=[incident.pk, Incident.Status.RESOLVED]), {
            'resolution_comment': 'Resuelto.',
        })

        self.assertRedirects(response, reverse('incidents:list'))
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.RESOLVED)
        self.assertEqual(incident.resolved_by, admin_user)

    def test_admin_with_company_cannot_resolve_other_company_incident(self):
        company = self.set_employee_company()
        other_company = Company.objects.create(name='Empresa B')
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        incident = Incident.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.OTHER,
            description='Incidencia empresa B.',
            created_by=other_user,
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('incidents:resolve', args=[incident.pk, Incident.Status.RESOLVED]), {
            'resolution_comment': 'Resuelto.',
        })

        self.assertEqual(response.status_code, 404)
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.PENDING)
        self.assertIsNone(incident.resolved_by)

    def test_user_without_profile_cannot_resolve_incidents(self):
        other_company = Company.objects.create(name='Empresa B')
        admin_user = User.objects.create_user(username='admin', password='secret')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        incident = Incident.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 7, 1),
            incident_type=Incident.IncidentType.OTHER,
            description='Incidencia empresa B.',
            created_by=other_user,
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('incidents:resolve', args=[incident.pk, Incident.Status.RESOLVED]), {
            'resolution_comment': 'Resuelto.',
        })

        self.assertEqual(response.status_code, 403)
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.PENDING)
        self.assertIsNone(incident.resolved_by)

# Create your tests here.
