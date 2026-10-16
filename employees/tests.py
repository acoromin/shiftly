from datetime import date

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from companies.models import Company, Workplace

from .models import EmployeeProfile
from .selectors import active_employees_for_company, employees_for_company


class EmployeeProfileTests(TestCase):
    def employee_form_payload(self, *, username='ana.actualizada', full_name='Ana Actualizada'):
        return {
            'username': username,
            'password': '',
            'password_confirm': '',
            'full_name': full_name,
            'email': 'ana@example.com',
            'phone': '',
            'dni_nie': '',
            'start_date': '2026-01-01',
            'end_date': '',
            'role': EmployeeProfile.Role.WORKER,
            'primary_position': EmployeeProfile.Position.WAITER,
            'contract_type': EmployeeProfile.ContractType.FULL_TIME,
            'weekly_contracted_hours': '40',
            'base_monthly_salary': '',
            'hourly_rate': '',
            'internal_notes': '',
        }

    def test_profile_can_reference_company_and_primary_workplace(self):
        company = Company.objects.create(name='Empresa A')
        workplace = Workplace.objects.create(company=company, name='Centro A')
        user = User.objects.create_user(username='ana', password='secret')

        profile = EmployeeProfile.objects.create(
            user=user,
            company=company,
            primary_workplace=workplace,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

        self.assertEqual(profile.company, company)
        self.assertEqual(profile.primary_workplace, workplace)
        self.assertEqual(profile.primary_position, EmployeeProfile.Position.WAITER)

    def test_profile_requires_company(self):
        user = User.objects.create_user(username='ana', password='secret')
        profile = EmployeeProfile(
            user=user,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn('company', context.exception.message_dict)
        self.assertIsNone(profile.primary_workplace)

    def test_primary_workplace_must_belong_to_profile_company(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        workplace = Workplace.objects.create(company=other_company, name='Centro B')
        user = User.objects.create_user(username='ana', password='secret')
        profile = EmployeeProfile(
            user=user,
            company=company,
            primary_workplace=workplace,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn('primary_workplace', context.exception.message_dict)

    def test_primary_workplace_requires_company(self):
        company = Company.objects.create(name='Empresa A')
        workplace = Workplace.objects.create(company=company, name='Centro A')
        user = User.objects.create_user(username='ana', password='secret')
        profile = EmployeeProfile(
            user=user,
            primary_workplace=workplace,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn('company', context.exception.message_dict)

    def test_employees_for_company_only_returns_company_employees(self):
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
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.assertEqual(list(employees_for_company(company)), [employee])
        self.assertFalse(employees_for_company(None).exists())

    def test_active_employees_for_company_excludes_inactive_and_other_company(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        user = User.objects.create_user(username='ana', password='secret')
        active = EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        inactive_user = User.objects.create_user(username='maria', password='secret')
        EmployeeProfile.objects.create(
            user=inactive_user,
            company=company,
            full_name='Maria Lopez',
            start_date=date(2026, 1, 1),
            is_active=False,
        )
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        self.assertEqual(list(active_employees_for_company(company)), [active])
        self.assertFalse(active_employees_for_company(None).exists())

    def test_profile_string_uses_full_name(self):
        company = Company.objects.create(name='Empresa A')
        user = User.objects.create_user(username='ana', password='secret')
        profile = EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.WORKER,
        )

        self.assertEqual(str(profile), 'Ana Garcia')
        self.assertTrue(profile.is_worker)
        self.assertEqual(profile.get_role_display(), 'Trabajador')

    def test_django_admin_exposes_company_without_primary_workplace(self):
        model_admin = admin.site._registry[EmployeeProfile]
        fields = [field for _name, options in model_admin.fieldsets for field in options['fields']]

        self.assertIn('company', fields)
        self.assertIn('company', model_admin.autocomplete_fields)
        self.assertNotIn('primary_workplace', fields)

    def test_admin_creates_user_and_employee_in_one_form(self):
        company = Company.objects.create(name='Empresa A')
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('employees:create'), {
            'username': 'maria',
            'password': 'UnaClaveSegura2026!',
            'password_confirm': 'UnaClaveSegura2026!',
            'full_name': 'Maria Lopez',
            'email': 'maria@example.com',
            'phone': '',
            'dni_nie': '',
            'start_date': '2026-06-23',
            'end_date': '',
            'role': EmployeeProfile.Role.WORKER,
            'primary_position': EmployeeProfile.Position.COOK,
            'contract_type': EmployeeProfile.ContractType.FULL_TIME,
            'weekly_contracted_hours': '40',
            'base_monthly_salary': '',
            'hourly_rate': '',
            'internal_notes': '',
        })

        self.assertRedirects(response, reverse('employees:list'))
        self.assertTrue(User.objects.filter(username='maria').exists())
        employee = EmployeeProfile.objects.get(full_name='Maria Lopez')
        self.assertEqual(employee.company, company)

    def test_admin_create_employee_assigns_company_and_primary_workplace(self):
        company = Company.objects.create(name='Empresa A')
        workplace = Workplace.objects.create(company=company, name='Centro A')
        admin_user = User.objects.create_user(username='admin', password='secret')
        EmployeeProfile.objects.create(
            user=admin_user,
            company=company,
            primary_workplace=workplace,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('employees:create'), {
            'username': 'maria',
            'password': 'UnaClaveSegura2026!',
            'password_confirm': 'UnaClaveSegura2026!',
            'full_name': 'Maria Lopez',
            'email': 'maria@example.com',
            'phone': '',
            'dni_nie': '',
            'start_date': '2026-06-23',
            'end_date': '',
            'role': EmployeeProfile.Role.WORKER,
            'primary_position': EmployeeProfile.Position.COOK,
            'contract_type': EmployeeProfile.ContractType.FULL_TIME,
            'weekly_contracted_hours': '40',
            'base_monthly_salary': '',
            'hourly_rate': '',
            'internal_notes': '',
        })

        self.assertRedirects(response, reverse('employees:list'))
        employee = EmployeeProfile.objects.get(user__username='maria')
        self.assertEqual(employee.company, company)
        self.assertEqual(employee.primary_workplace, workplace)

    def test_admin_with_company_only_sees_company_employees(self):
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
        EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('employees:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana Garcia')
        self.assertNotContains(response, 'Luis Perez')

    def test_admin_with_company_active_count_uses_company_employees(self):
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
        EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        inactive_user = User.objects.create_user(username='maria', password='secret')
        EmployeeProfile.objects.create(
            user=inactive_user,
            company=company,
            full_name='Maria Lopez',
            start_date=date(2026, 1, 1),
            is_active=False,
        )
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('employees:list'))

        self.assertEqual(response.context['active_count'], 2)
        self.assertContains(response, '2 trabajadores activos')

    def test_admin_can_edit_employee(self):
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
        employee = EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('employees:edit', args=[employee.pk]), self.employee_form_payload())

        self.assertRedirects(response, reverse('employees:list'))
        employee.refresh_from_db()
        worker_user.refresh_from_db()
        self.assertEqual(employee.full_name, 'Ana Actualizada')
        self.assertEqual(worker_user.username, 'ana.actualizada')

    def test_admin_with_company_can_edit_company_employee(self):
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
        employee = EmployeeProfile.objects.create(
            user=worker_user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('employees:edit', args=[employee.pk]), self.employee_form_payload())

        self.assertRedirects(response, reverse('employees:list'))
        employee.refresh_from_db()
        self.assertEqual(employee.full_name, 'Ana Actualizada')

    def test_admin_with_company_cannot_edit_other_company_employee(self):
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
        worker_user = User.objects.create_user(username='luis', password='secret')
        employee = EmployeeProfile.objects.create(
            user=worker_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('employees:edit', args=[employee.pk]), self.employee_form_payload())

        self.assertEqual(response.status_code, 404)
        employee.refresh_from_db()
        self.assertEqual(employee.full_name, 'Luis Perez')

    def test_admin_with_company_cannot_toggle_other_company_employee(self):
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
        worker_user = User.objects.create_user(username='luis', password='secret')
        employee = EmployeeProfile.objects.create(
            user=worker_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('employees:toggle-active', args=[employee.pk]))

        self.assertEqual(response.status_code, 404)
        employee.refresh_from_db()
        self.assertTrue(employee.is_active)

    def test_admin_with_company_cannot_change_other_company_employee_password(self):
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
        worker_user = User.objects.create_user(username='luis', password='secret')
        employee = EmployeeProfile.objects.create(
            user=worker_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('employees:password', args=[employee.pk]), {
            'password': 'OtraClaveSegura2026!',
            'password_confirm': 'OtraClaveSegura2026!',
        })

        self.assertEqual(response.status_code, 404)

    def test_user_without_profile_cannot_manage_employees(self):
        other_company = Company.objects.create(name='Empresa B')
        user_without_profile = User.objects.create_user(username='sinperfil', password='secret')
        worker_user = User.objects.create_user(username='luis', password='secret')
        employee = EmployeeProfile.objects.create(
            user=worker_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(user_without_profile)

        response = self.client.post(reverse('employees:edit', args=[employee.pk]), self.employee_form_payload())

        self.assertEqual(response.status_code, 403)
        employee.refresh_from_db()
        self.assertEqual(employee.full_name, 'Luis Perez')

    def test_worker_cannot_manage_employees(self):
        company = Company.objects.create(name='Empresa A')
        user = User.objects.create_user(username='ana', password='secret')
        EmployeeProfile.objects.create(
            user=user,
            company=company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(user)

        response = self.client.get(reverse('employees:list'))

        self.assertEqual(response.status_code, 403)

# Create your tests here.
