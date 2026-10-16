from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from companies.models import Company
from employees.models import EmployeeProfile
from payroll.models import PayrollDraft


class ReportsTests(TestCase):
    def test_admin_can_download_payroll_csv(self):
        company = Company.objects.create(name='Empresa A')
        user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Admin',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        worker_user = User.objects.create_user(username='ana', password='secret')
        EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

        self.client.force_login(user)
        response = self.client.get(reverse('reports:payroll-csv') + '?year=2026&month=6')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        content = response.content.decode()
        self.assertEqual(
            content.splitlines()[0],
            'empleado,mes,horas_contratadas,horas_planificadas,horas_fichadas_validas,'
            'horas_pendientes_revision,horas_extra_detectadas,horas_extra_aprobadas,'
            'vacaciones_aprobadas,dias_libres_aprobados,ausencias,incidencias_pendientes,observaciones',
        )
        self.assertIn('Ana Garcia', content)

    def test_admin_with_company_downloads_company_payroll_csv(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Admin',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        first_user = User.objects.create_user(username='ana', password='secret')
        EmployeeProfile.objects.create(
            user=first_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        second_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=second_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(user)
        response = self.client.get(reverse('reports:payroll-csv') + '?year=2026&month=6')

        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ana Garcia', content)
        self.assertNotIn('Luis Perez', content)

    def test_user_without_profile_cannot_download_payroll_csv(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        user = User.objects.create_user(username='admin', password='secret')
        first_user = User.objects.create_user(username='ana', password='secret')
        EmployeeProfile.objects.create(
            user=first_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        second_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=second_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        self.client.force_login(user)
        response = self.client.get(reverse('reports:payroll-csv') + '?year=2026&month=6')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(PayrollDraft.objects.exists())

    def test_monthly_summary_lists_current_active_employees(self):
        company = Company.objects.create(name='Empresa A')
        user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Admin',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        first_user = User.objects.create_user(username='ana', password='secret')
        EmployeeProfile.objects.create(
            user=first_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        second_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=second_user,
            company=company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        self.client.force_login(user)
        response = self.client.get(reverse('reports:monthly-summary') + '?year=2026&month=6')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana Garcia')
        self.assertContains(response, 'Luis Perez')

    def test_monthly_summary_filters_by_admin_company_when_available(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Admin',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        first_user = User.objects.create_user(username='ana', password='secret')
        EmployeeProfile.objects.create(
            user=first_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        second_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=second_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(user)
        response = self.client.get(reverse('reports:monthly-summary') + '?year=2026&month=6')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana Garcia')
        self.assertNotContains(response, 'Luis Perez')

    def test_worker_cannot_view_monthly_summary(self):
        company = Company.objects.create(name='Empresa A')
        user = User.objects.create_user(username='ana', password='secret')
        EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

        self.client.force_login(user)
        response = self.client.get(reverse('reports:monthly-summary'))

        self.assertEqual(response.status_code, 403)

# Create your tests here.
