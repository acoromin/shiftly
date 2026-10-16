from datetime import date

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from companies.models import Company
from employees.models import EmployeeProfile

from .models import LeaveRequest
from .selectors import leave_requests_for_company, leave_requests_for_employee


class LeaveRequestTests(TestCase):
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

    def test_request_can_reference_company(self):
        company = self.set_employee_company()

        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            company=company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )

        self.assertEqual(leave_request.company, company)

    def test_request_requires_company(self):
        leave_request = LeaveRequest(
            employee=self.employee,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )

        with self.assertRaises(ValidationError) as context:
            leave_request.full_clean()

        self.assertIn('company', context.exception.message_dict)

    def test_request_employee_must_belong_to_request_company(self):
        self.set_employee_company(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        leave_request = LeaveRequest(
            employee=self.employee,
            company=other_company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )

        with self.assertRaises(ValidationError) as context:
            leave_request.full_clean()

        self.assertIn('employee', context.exception.message_dict)

    def test_leave_requests_for_company_only_returns_company_requests(self):
        company = self.set_employee_company()
        other_user = User.objects.create_user(username='luis', password='secret')
        other_company = Company.objects.create(name='Empresa B')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            company=company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        LeaveRequest.objects.create(
            employee=other_employee,
            company=other_company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )
        self.assertEqual(list(leave_requests_for_company(company)), [leave_request])
        self.assertFalse(leave_requests_for_company(None).exists())

    def test_leave_requests_for_employee_only_returns_employee_requests(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            company=self.employee.company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        LeaveRequest.objects.create(
            employee=other,
            company=other.company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )

        self.assertEqual(list(leave_requests_for_employee(self.employee)), [leave_request])

    def test_django_admin_exposes_company(self):
        model_admin = admin.site._registry[LeaveRequest]

        self.assertIn('company', model_admin.list_display)
        self.assertIn('company', model_admin.list_filter)
        self.assertIn('company', model_admin.autocomplete_fields)

    def test_worker_can_create_request(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('leaves:create-typed', args=[LeaveRequest.RequestType.VACATION]), {
            'request_type': LeaveRequest.RequestType.VACATION,
            'start_date': '2026-07-01',
            'end_date': '2026-07-02',
            'worker_comment': 'Necesito esos dias.',
        })

        self.assertRedirects(response, reverse('leaves:list'))
        self.assertTrue(LeaveRequest.objects.filter(employee=self.employee).exists())

    def test_worker_create_request_saves_company(self):
        company = self.set_employee_company()
        self.client.force_login(self.user)

        response = self.client.post(reverse('leaves:create-typed', args=[LeaveRequest.RequestType.VACATION]), {
            'request_type': LeaveRequest.RequestType.VACATION,
            'start_date': '2026-07-01',
            'end_date': '2026-07-02',
            'worker_comment': 'Necesito esos dias.',
        })

        self.assertRedirects(response, reverse('leaves:list'))
        leave_request = LeaveRequest.objects.get(employee=self.employee)
        self.assertEqual(leave_request.company, company)

    def test_admin_can_approve_request(self):
        company = self.set_employee_company()
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            company=company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('leaves:review', args=[leave_request.pk, LeaveRequest.Status.APPROVED]), {
            'admin_comment': 'Aprobado.',
        })

        self.assertRedirects(response, reverse('leaves:list'))
        leave_request.refresh_from_db()
        self.assertEqual(leave_request.status, LeaveRequest.Status.APPROVED)

    def test_admin_with_company_can_review_company_request(self):
        company = self.set_employee_company()
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            company=company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('leaves:review', args=[leave_request.pk, LeaveRequest.Status.APPROVED]), {
            'admin_comment': 'Aprobado.',
        })

        self.assertRedirects(response, reverse('leaves:list'))
        leave_request.refresh_from_db()
        self.assertEqual(leave_request.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(leave_request.reviewed_by, admin_user)

    def test_admin_with_company_cannot_review_other_company_request(self):
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
        leave_request = LeaveRequest.objects.create(
            employee=other,
            company=other_company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('leaves:review', args=[leave_request.pk, LeaveRequest.Status.APPROVED]), {
            'admin_comment': 'Aprobado.',
        })

        self.assertEqual(response.status_code, 404)
        leave_request.refresh_from_db()
        self.assertEqual(leave_request.status, LeaveRequest.Status.PENDING)
        self.assertIsNone(leave_request.reviewed_by)

    def test_user_without_profile_cannot_review_requests(self):
        other_company = Company.objects.create(name='Empresa B')
        admin_user = User.objects.create_user(username='admin', password='secret')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        leave_request = LeaveRequest.objects.create(
            employee=other,
            company=other_company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('leaves:review', args=[leave_request.pk, LeaveRequest.Status.APPROVED]), {
            'admin_comment': 'Aprobado.',
        })

        self.assertEqual(response.status_code, 403)
        leave_request.refresh_from_db()
        self.assertEqual(leave_request.status, LeaveRequest.Status.PENDING)
        self.assertIsNone(leave_request.reviewed_by)

    def test_admin_with_company_only_sees_company_requests(self):
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
        LeaveRequest.objects.create(
            employee=self.employee,
            company=company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        LeaveRequest.objects.create(
            employee=other,
            company=other_company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('leaves:list'))

        self.assertContains(response, '01/07/2026')
        self.assertNotContains(response, '01/08/2026')

    def test_user_without_profile_requests_list_is_empty(self):
        unassigned_user = User.objects.create_user(username='sinperfil', password='secret')
        LeaveRequest.objects.create(
            employee=self.employee,
            company=self.employee.company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )

        self.client.force_login(unassigned_user)
        response = self.client.get(reverse('leaves:list'))

        self.assertContains(response, 'No hay solicitudes.')
        self.assertNotContains(response, '01/07/2026')

    def test_worker_only_sees_own_requests(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        LeaveRequest.objects.create(
            employee=self.employee,
            company=self.employee.company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        LeaveRequest.objects.create(
            employee=other,
            company=other.company,
            request_type=LeaveRequest.RequestType.DAY_OFF,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 1),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('leaves:list'))

        self.assertContains(response, '01/07/2026')
        self.assertNotContains(response, '01/08/2026')

    def test_worker_cannot_review_request(self):
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            company=self.employee.company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('leaves:review', args=[leave_request.pk, 'approved']))

        self.assertEqual(response.status_code, 403)

    def test_worker_request_menu_offers_mvp_request_types(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('leaves:create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comunicar ausencia')
        self.assertContains(response, 'Comunicar baja médica')
        self.assertContains(response, 'Solicitar vacaciones')
        self.assertContains(response, 'Solicitar día libre')

    def test_worker_can_cancel_own_pending_request(self):
        leave_request = LeaveRequest.objects.create(
            employee=self.employee,
            company=self.employee.company,
            request_type=LeaveRequest.RequestType.VACATION,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('leaves:cancel', args=[leave_request.pk]))

        self.assertRedirects(response, reverse('leaves:list'))
        leave_request.refresh_from_db()
        self.assertEqual(leave_request.status, LeaveRequest.Status.CANCELLED)

# Create your tests here.
