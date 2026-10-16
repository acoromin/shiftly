from datetime import date, time

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from companies.models import Company, Workplace
from employees.models import EmployeeProfile

from .forms import ShiftForm
from .models import Shift
from .selectors import shifts_for_company, shifts_for_employee


class ShiftTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa Base')
        self.user = User.objects.create_user(username='ana', password='secret')
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            company=self.company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )

    def set_employee_context(self, employee=None, company_name='Empresa A', workplace_name='Centro A'):
        employee = employee or self.employee
        company = Company.objects.create(name=company_name)
        workplace = Workplace.objects.create(company=company, name=workplace_name)
        employee.company = company
        employee.primary_workplace = workplace
        employee.save(update_fields=['company', 'primary_workplace'])
        return company, workplace

    def test_shift_can_reference_company_and_workplace(self):
        company = Company.objects.create(name='Empresa A')
        workplace = Workplace.objects.create(company=company, name='Centro A')
        self.employee.company = company
        self.employee.primary_workplace = workplace
        self.employee.save(update_fields=['company', 'primary_workplace'])

        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        self.assertEqual(shift.company, company)
        self.assertEqual(shift.workplace, workplace)
        self.assertEqual(shift.position, Shift.Position.WAITER)

    def test_shift_requires_company(self):
        shift = Shift(
            employee=self.employee,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        with self.assertRaises(ValidationError) as context:
            shift.full_clean()

        self.assertIn('company', context.exception.message_dict)
        self.assertIsNone(shift.workplace)

    def test_shift_employee_must_belong_to_shift_company(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        self.employee.company = company
        self.employee.save(update_fields=['company'])
        shift = Shift(
            employee=self.employee,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        with self.assertRaises(ValidationError) as context:
            shift.full_clean()

        self.assertIn('employee', context.exception.message_dict)

    def test_shift_workplace_must_belong_to_shift_company(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        workplace = Workplace.objects.create(company=other_company, name='Centro B')
        self.employee.company = company
        self.employee.save(update_fields=['company'])
        shift = Shift(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        with self.assertRaises(ValidationError) as context:
            shift.full_clean()

        self.assertIn('workplace', context.exception.message_dict)

    def test_shift_workplace_requires_company(self):
        company = Company.objects.create(name='Empresa A')
        workplace = Workplace.objects.create(company=company, name='Centro A')
        shift = Shift(
            employee=self.employee,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        with self.assertRaises(ValidationError) as context:
            shift.full_clean()

        self.assertIn('company', context.exception.message_dict)

    def test_shifts_for_company_only_returns_company_shifts(self):
        company, workplace = self.set_employee_context()
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        Shift.objects.create(
            employee=other_employee,
            company=other_employee.company,
            date=date(2026, 6, 23),
            start_time=time(16, 0),
            end_time=time(23, 0),
        )
        self.assertEqual(list(shifts_for_company(company)), [shift])
        self.assertFalse(shifts_for_company(None).exists())

    def test_shifts_for_employee_only_returns_employee_shifts(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        Shift.objects.create(
            employee=other_employee,
            company=other_employee.company,
            date=date(2026, 6, 23),
            start_time=time(16, 0),
            end_time=time(23, 0),
        )

        self.assertEqual(list(shifts_for_employee(self.employee)), [shift])

    def test_planned_duration_subtracts_break(self):
        shift = Shift(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
            planned_break_minutes=30,
        )

        self.assertEqual(shift.planned_duration_hours, 7.5)

    def test_rejects_overlapping_shift_for_same_employee(self):
        Shift.objects.create(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        shift = Shift(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 6, 23),
            start_time=time(15, 0),
            end_time=time(23, 0),
        )

        with self.assertRaises(ValidationError):
            shift.full_clean()

    def test_worker_week_view_only_shows_own_shifts(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        Shift.objects.create(
            employee=self.employee,
            company=self.employee.company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        Shift.objects.create(
            employee=other,
            company=other.company,
            date=date(2026, 6, 23),
            start_time=time(16, 0),
            end_time=time(23, 0),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('scheduling:week') + '?week=2026-06-23')

        self.assertContains(response, '08:00 - 16:00')
        self.assertContains(response, '8,00 h planificadas')
        self.assertNotContains(response, '16:00 - 23:00')

    def test_django_admin_exposes_company_without_workplace(self):
        model_admin = admin.site._registry[Shift]
        fields = [field for _name, options in model_admin.fieldsets for field in options['fields']]

        self.assertIn('company', fields)
        self.assertIn('company', model_admin.autocomplete_fields)
        self.assertNotIn('workplace', fields)

    def test_admin_week_view_shows_team_shifts(self):
        company, _workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=company,
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
        Shift.objects.create(
            employee=other,
            company=company,
            date=date(2026, 6, 23),
            start_time=time(16, 0),
            end_time=time(23, 0),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('scheduling:week') + '?week=2026-06-23')

        self.assertContains(response, '08:00 - 16:00')
        self.assertContains(response, '16:00 - 23:00')
        self.assertContains(response, 'Luis Perez')

    def test_admin_with_company_week_view_only_shows_company_shifts(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        Shift.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(16, 0),
            end_time=time(23, 0),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('scheduling:week') + '?week=2026-06-23')

        self.assertContains(response, '08:00 - 16:00')
        self.assertNotContains(response, '16:00 - 23:00')
        self.assertNotContains(response, 'Luis Perez')

    def test_admin_with_company_month_view_only_shows_company_shifts(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        Shift.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(16, 0),
            end_time=time(23, 0),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('scheduling:month') + '?year=2026&month=6')

        self.assertContains(response, 'Ana Garcia')
        self.assertNotContains(response, 'Luis Perez')

    def test_admin_with_company_create_shift_form_only_lists_company_employees(self):
        self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('scheduling:create'))

        employees = response.context['form'].fields['employee'].queryset
        self.assertIn(self.employee, employees)
        self.assertNotIn(other, employees)

    def test_shift_form_with_company_rejects_other_company_employee(self):
        company, _workplace = self.set_employee_context()
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        form = ShiftForm({
            'employee': other.pk,
            'date': '2026-06-23',
            'start_time': '08:00',
            'end_time': '16:00',
            'planned_break_minutes': '30',
            'position': Shift.Position.WAITER,
            'notes': '',
        }, company=company)

        self.assertFalse(form.is_valid())
        self.assertIn('employee', form.errors)

    def test_admin_with_company_cannot_create_shift_for_other_company_employee(self):
        self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:create'), {
            'employee': other.pk,
            'date': '2026-06-23',
            'start_time': '08:00',
            'end_time': '16:00',
            'planned_break_minutes': '30',
            'position': Shift.Position.WAITER,
            'notes': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Shift.objects.filter(employee=other).exists())

    def test_admin_can_cancel_shift_logically(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:cancel', args=[shift.pk]))

        self.assertEqual(response.status_code, 302)
        shift.refresh_from_db()
        self.assertFalse(shift.is_active)

    def test_admin_with_company_can_cancel_company_shift(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:cancel', args=[shift.pk]))

        self.assertEqual(response.status_code, 302)
        shift.refresh_from_db()
        self.assertFalse(shift.is_active)

    def test_admin_create_shift_saves_employee_company_and_workplace(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:create'), {
            'employee': self.employee.pk,
            'date': '2026-06-23',
            'start_time': '08:00',
            'end_time': '16:00',
            'planned_break_minutes': '30',
            'position': Shift.Position.WAITER,
            'notes': '',
        })

        self.assertRedirects(response, reverse('scheduling:week'))
        shift = Shift.objects.get(employee=self.employee, date=date(2026, 6, 23))
        self.assertEqual(shift.company, company)
        self.assertEqual(shift.workplace, workplace)

    def test_admin_can_edit_shift(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:edit', args=[shift.pk]), {
            'employee': self.employee.pk,
            'date': '2026-06-23',
            'start_time': '09:00',
            'end_time': '17:00',
            'planned_break_minutes': '45',
            'position': Shift.Position.COOK,
            'notes': 'Cambio de horario.',
        })

        self.assertRedirects(response, reverse('scheduling:week') + '?week=2026-06-23')
        shift.refresh_from_db()
        self.assertEqual(shift.start_time, time(9, 0))
        self.assertEqual(shift.end_time, time(17, 0))
        self.assertEqual(shift.company, company)
        self.assertEqual(shift.workplace, workplace)

    def test_admin_with_company_cannot_reassign_company_shift_to_other_company_employee(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:edit', args=[shift.pk]), {
            'employee': other.pk,
            'date': '2026-06-23',
            'start_time': '09:00',
            'end_time': '17:00',
            'planned_break_minutes': '45',
            'position': Shift.Position.COOK,
            'notes': 'Cambio de horario.',
        })

        self.assertEqual(response.status_code, 200)
        shift.refresh_from_db()
        self.assertEqual(shift.employee, self.employee)
        self.assertEqual(shift.start_time, time(8, 0))
        self.assertEqual(shift.company, company)
        self.assertEqual(shift.workplace, workplace)

    def test_admin_with_company_cannot_edit_other_company_shift(self):
        self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:edit', args=[shift.pk]), {
            'employee': other.pk,
            'date': '2026-06-23',
            'start_time': '09:00',
            'end_time': '17:00',
            'planned_break_minutes': '45',
            'position': Shift.Position.COOK,
            'notes': 'Cambio de horario.',
        })

        self.assertEqual(response.status_code, 404)
        shift.refresh_from_db()
        self.assertEqual(shift.start_time, time(8, 0))

    def test_duplicate_shift_saves_employee_company_and_workplace(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:duplicate', args=[shift.pk]))

        self.assertEqual(response.status_code, 302)
        duplicate = Shift.objects.get(employee=self.employee, date=date(2026, 6, 30))
        self.assertEqual(duplicate.company, company)
        self.assertEqual(duplicate.workplace, workplace)

    def test_admin_with_company_cannot_duplicate_other_company_shift(self):
        self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:duplicate', args=[shift.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Shift.objects.filter(employee=other).count(), 1)

    def test_admin_with_company_cannot_cancel_other_company_shift(self):
        self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:cancel', args=[shift.pk]))

        self.assertEqual(response.status_code, 404)
        shift.refresh_from_db()
        self.assertTrue(shift.is_active)

    def test_user_without_profile_cannot_manage_shifts(self):
        other_company = Company.objects.create(name='Empresa B')
        user_without_profile = User.objects.create_user(username='sinperfil', password='secret')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(user_without_profile)

        edit_response = self.client.post(reverse('scheduling:edit', args=[shift.pk]), {
            'employee': other.pk,
            'date': '2026-06-23',
            'start_time': '09:00',
            'end_time': '17:00',
            'planned_break_minutes': '45',
            'position': Shift.Position.COOK,
            'notes': 'Cambio de horario.',
        })
        duplicate_response = self.client.post(reverse('scheduling:duplicate', args=[shift.pk]))
        cancel_response = self.client.post(reverse('scheduling:cancel', args=[shift.pk]))

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(duplicate_response.status_code, 403)
        self.assertEqual(cancel_response.status_code, 403)
        shift.refresh_from_db()
        self.assertEqual(shift.start_time, time(8, 0))
        self.assertTrue(shift.is_active)

    def test_copy_previous_week_saves_employee_company_and_workplace(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:copy-week') + '?week=2026-06-29')

        self.assertEqual(response.status_code, 302)
        copied = Shift.objects.get(employee=self.employee, date=date(2026, 6, 30))
        self.assertEqual(copied.company, company)
        self.assertEqual(copied.workplace, workplace)

    def test_copy_previous_week_with_company_does_not_copy_other_company_shifts(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        Shift.objects.create(
            employee=other,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(16, 0),
            end_time=time(23, 0),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('scheduling:copy-week') + '?week=2026-06-29')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Shift.objects.filter(employee=self.employee, date=date(2026, 6, 30)).exists())
        self.assertFalse(Shift.objects.filter(employee=other, date=date(2026, 6, 30)).exists())

# Create your tests here.
