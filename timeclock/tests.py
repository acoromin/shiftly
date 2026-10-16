from datetime import date, time, timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from companies.models import Company, Workplace
from core.models import BusinessConfig
from employees.models import EmployeeProfile
from scheduling.models import Shift

from .forms import ManualTimeClockEntryForm
from .models import TimeClockEntry
from .selectors import timeclock_entries_for_company, timeclock_entries_for_employee
from .services import attempt_clock, employees_with_open_clock_entries, ensure_missing_clock_incident, resolve_timeclock_entry_context


class TimeClockTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa Base')
        self.user = User.objects.create_user(username='ana', password='secret')
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            company=self.company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        self.config = BusinessConfig.get_solo()
        self.config.public_wifi_ip = '203.0.113.10'
        self.config.set_qr_token('valid-token')
        self.config.save()
        self.factory = RequestFactory()

    def request(self, ip='203.0.113.10'):
        request = self.factory.post('/fichar/', {'token': 'valid-token'}, REMOTE_ADDR=ip)
        request.user = self.user
        return request

    def set_employee_context(self, employee=None, company_name='Empresa A', workplace_name='Centro A'):
        employee = employee or self.employee
        company = Company.objects.create(name=company_name)
        workplace = Workplace.objects.create(company=company, name=workplace_name)
        employee.company = company
        employee.primary_workplace = workplace
        employee.save(update_fields=['company', 'primary_workplace'])
        return company, workplace

    def test_resolve_context_uses_employee_company_and_primary_workplace(self):
        company, workplace = self.set_employee_context()

        context = resolve_timeclock_entry_context(self.employee)

        self.assertEqual(context['company'], company)
        self.assertEqual(context['workplace'], workplace)

    def test_open_clock_entries_require_explicit_employee_scope(self):
        with self.assertNumQueries(0), self.assertRaises(ValueError):
            employees_with_open_clock_entries()
        with self.assertNumQueries(0), self.assertRaises(ValueError):
            employees_with_open_clock_entries(None)
        self.assertEqual(employees_with_open_clock_entries(EmployeeProfile.objects.none()), [])

    def test_manual_form_without_company_rejects_edit_without_clearing_existing_company(self):
        company, workplace = self.set_employee_context()
        entry = TimeClockEntry.objects.create(
            employee=self.employee, company=company, workplace=workplace,
            entry_type=TimeClockEntry.EntryType.IN, timestamp=timezone.now(), created_by=self.user,
        )
        form = ManualTimeClockEntryForm({
            'employee': self.employee.pk, 'entry_type': TimeClockEntry.EntryType.OUT,
            'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'manual_reason': 'Correccion sin contexto.',
        }, instance=entry)
        self.assertFalse(form.is_valid())
        self.assertIn('employee', form.errors)
        entry.refresh_from_db()
        self.assertEqual(entry.company, company)
        self.assertEqual(entry.entry_type, TimeClockEntry.EntryType.IN)

    def test_worker_hours_page_passes_company_to_summary(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('timeclock:hours') + '?year=2026&month=6')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['summary'].company, self.company)

    def test_valid_clock_saves_company_and_employee_primary_workplace(self):
        company, workplace = self.set_employee_context()

        ok, message, entry = attempt_clock(self.request(), self.employee, 'valid-token')

        self.assertTrue(ok)
        self.assertEqual(message, 'Entrada registrada correctamente.')
        self.assertEqual(entry.company, company)
        self.assertEqual(entry.workplace, workplace)

    def test_valid_clock_prefers_related_shift_workplace(self):
        company, _employee_workplace = self.set_employee_context()
        shift_workplace = Workplace.objects.create(company=company, name='Centro turno')
        shift = Shift.objects.create(
            employee=self.employee,
            company=company,
            workplace=shift_workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        ok, _message, entry = attempt_clock(self.request(), self.employee, 'valid-token', related_shift=shift)

        self.assertTrue(ok)
        self.assertEqual(entry.related_shift, shift)
        self.assertEqual(entry.company, company)
        self.assertEqual(entry.workplace, shift_workplace)

    def test_entry_can_reference_company_and_workplace(self):
        company = Company.objects.create(name='Empresa A')
        workplace = Workplace.objects.create(company=company, name='Centro A')
        self.employee.company = company
        self.employee.primary_workplace = workplace
        self.employee.save(update_fields=['company', 'primary_workplace'])

        entry = TimeClockEntry.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        self.assertEqual(entry.company, company)
        self.assertEqual(entry.workplace, workplace)

    def test_entry_requires_company(self):
        entry = TimeClockEntry(
            employee=self.employee,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            entry.full_clean()

        self.assertIn('company', context.exception.message_dict)
        with self.assertRaises(ValidationError):
            entry.save()
        self.assertFalse(TimeClockEntry.objects.exists())

    def test_database_rejects_missing_company_even_without_model_validation(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TimeClockEntry.objects.bulk_create([TimeClockEntry(
                employee=self.employee,
                entry_type=TimeClockEntry.EntryType.IN,
                timestamp=timezone.now(),
                created_by=self.user,
            )])

    def test_entry_allows_empty_workplace_with_company(self):
        entry = TimeClockEntry.objects.create(
            employee=self.employee,
            company=self.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            created_by=self.user,
        )

        entry.refresh_from_db()
        self.assertIsNone(entry.workplace)

    def test_save_rejects_company_change_that_mismatches_employee(self):
        entry = TimeClockEntry.objects.create(
            employee=self.employee,
            company=self.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            created_by=self.user,
        )
        entry.company = Company.objects.create(name='Empresa B')

        with self.assertRaises(ValidationError) as context:
            entry.save(update_fields=['company'])

        self.assertIn('employee', context.exception.message_dict)
        entry.refresh_from_db()
        self.assertEqual(entry.company, self.company)

    def test_resolve_context_requires_employee_company(self):
        employee_without_company = EmployeeProfile(user=self.user, full_name='Sin empresa')

        for employee in (None, employee_without_company):
            with self.subTest(employee=employee), self.assertRaises(ValidationError) as context:
                resolve_timeclock_entry_context(employee)
            self.assertIn('company', context.exception.message_dict)

    def test_django_admin_exposes_required_company(self):
        model_admin = admin.site._registry[TimeClockEntry]
        request = self.factory.get('/admin/')
        request.user = self.user
        form = model_admin.get_form(request)

        self.assertTrue(form.base_fields['company'].required)
        self.assertIn('company', model_admin.autocomplete_fields)

    def test_entry_employee_must_belong_to_entry_company(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        self.employee.company = company
        self.employee.save(update_fields=['company'])
        entry = TimeClockEntry(
            employee=self.employee,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            entry.full_clean()

        self.assertIn('employee', context.exception.message_dict)

    def test_entry_workplace_must_belong_to_entry_company(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        workplace = Workplace.objects.create(company=other_company, name='Centro B')
        self.employee.company = company
        self.employee.save(update_fields=['company'])
        entry = TimeClockEntry(
            employee=self.employee,
            company=company,
            workplace=workplace,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            entry.full_clean()

        self.assertIn('workplace', context.exception.message_dict)

    def test_entry_workplace_requires_company(self):
        company = Company.objects.create(name='Empresa A')
        workplace = Workplace.objects.create(company=company, name='Centro A')
        entry = TimeClockEntry(
            employee=self.employee,
            workplace=workplace,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            entry.full_clean()

        self.assertIn('company', context.exception.message_dict)

    def test_related_shift_must_belong_to_entry_company(self):
        company = Company.objects.create(name='Empresa A')
        other_company = Company.objects.create(name='Empresa B')
        self.employee.company = company
        self.employee.save(update_fields=['company'])
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=other_employee,
            company=other_company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        entry = TimeClockEntry(
            employee=self.employee,
            company=company,
            related_shift=shift,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            entry.full_clean()

        self.assertIn('related_shift', context.exception.message_dict)

    def test_clock_rejects_related_shift_of_another_employee_in_same_company(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=self.company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        shift = Shift.objects.create(
            employee=other_employee,
            company=self.company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        with self.assertRaises(ValidationError) as context:
            attempt_clock(self.request(), self.employee, 'valid-token', related_shift=shift)

        self.assertIn('related_shift', context.exception.message_dict)
        self.assertFalse(TimeClockEntry.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_timeclock_entries_for_company_only_returns_company_entries(self):
        company, workplace = self.set_employee_context()
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        entry = TimeClockEntry.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 8, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        TimeClockEntry.objects.create(
            employee=other_employee,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 9, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )

        self.assertEqual(list(timeclock_entries_for_company(company)), [entry])
        self.assertFalse(timeclock_entries_for_company(None).exists())

    def test_timeclock_entries_for_employee_only_returns_employee_entries(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other_employee = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        entry = TimeClockEntry.objects.create(
            employee=self.employee,
            company=self.employee.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 8, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        TimeClockEntry.objects.create(
            employee=other_employee,
            company=other_employee.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 9, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )

        self.assertEqual(list(timeclock_entries_for_employee(self.employee)), [entry])

    def test_missing_clock_incident_saves_company_from_entry(self):
        company = self.employee.company
        TimeClockEntry.objects.create(
            employee=self.employee,
            company=company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now() - timedelta(hours=19),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        incident = ensure_missing_clock_incident(self.employee)

        self.assertEqual(incident.company, company)

    def test_blocks_invalid_qr(self):
        request = self.factory.post('/fichar/', {'token': 'bad-token'}, REMOTE_ADDR='203.0.113.10')
        request.user = self.user

        ok, message, entry = attempt_clock(request, self.employee, 'bad-token')

        self.assertFalse(ok)
        self.assertEqual(message, 'QR no válido o caducado.')
        self.assertEqual(entry.status, TimeClockEntry.Status.INVALID_QR)
        self.assertEqual(entry.company, self.company)

    def test_blocks_wrong_wifi_ip(self):
        ok, message, entry = attempt_clock(self.request(ip='198.51.100.7'), self.employee, 'valid-token')

        self.assertFalse(ok)
        self.assertEqual(message, 'Debes estar conectado al WiFi del bar para fichar.')
        self.assertEqual(entry.status, TimeClockEntry.Status.BLOCKED_IP)
        self.assertEqual(entry.company, self.company)

    def test_valid_clock_toggles_in_and_out(self):
        ok_in, message_in, entry_in = attempt_clock(self.request(), self.employee, 'valid-token')
        entry_in.timestamp = timezone.now() - timedelta(minutes=2)
        entry_in.save(update_fields=['timestamp'])
        ok_out, message_out, entry_out = attempt_clock(self.request(), self.employee, 'valid-token')

        self.assertTrue(ok_in)
        self.assertEqual(message_in, 'Entrada registrada correctamente.')
        self.assertEqual(entry_in.entry_type, TimeClockEntry.EntryType.IN)
        self.assertTrue(ok_out)
        self.assertEqual(message_out, 'Salida registrada correctamente.')
        self.assertEqual(entry_out.entry_type, TimeClockEntry.EntryType.OUT)

    def test_worker_cannot_access_manual_clock_form(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('timeclock:manual-create'))

        self.assertEqual(response.status_code, 403)

    def test_worker_history_only_shows_own_entries(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
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
            employee=other,
            company=other.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 9, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('timeclock:history'))

        self.assertContains(response, '08:00')
        self.assertNotContains(response, 'Luis Perez')

    def test_admin_history_shows_team_entries(self):
        company, _workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save()
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        TimeClockEntry.objects.create(
            employee=other,
            company=company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 9, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('timeclock:history'))

        self.assertContains(response, 'Luis Perez')

    def test_admin_with_company_history_only_shows_company_entries(self):
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
        TimeClockEntry.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 8, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        TimeClockEntry.objects.create(
            employee=other,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 9, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('timeclock:history'))

        self.assertContains(response, 'Ana Garcia')
        self.assertNotContains(response, 'Luis Perez')

    def test_user_without_profile_history_is_empty(self):
        unassigned_user = User.objects.create_user(username='sinperfil', password='secret')
        TimeClockEntry.objects.create(
            employee=self.employee,
            company=self.employee.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.make_aware(timezone.datetime(2026, 6, 23, 8, 0)),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )

        self.client.force_login(unassigned_user)
        response = self.client.get(reverse('timeclock:history'))

        self.assertContains(response, 'No hay fichajes.')
        self.assertNotContains(response, '08:00')

    def test_admin_manual_clock_form_uses_active_employee_queryset(self):
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
        inactive_user = User.objects.create_user(username='maria', password='secret')
        inactive = EmployeeProfile.objects.create(
            user=inactive_user,
            company=company,
            full_name='Maria Lopez',
            start_date=date(2026, 1, 1),
            is_active=False,
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('timeclock:manual-create'))

        self.assertEqual(response.status_code, 200)
        employees = response.context['form'].fields['employee'].queryset
        self.assertIn(self.employee, employees)
        self.assertIn(other, employees)
        self.assertNotIn(inactive, employees)

    def test_admin_with_company_manual_clock_form_only_lists_company_employees(self):
        self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('timeclock:manual-create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana Garcia')
        self.assertNotContains(response, 'Luis Perez')

    def test_manual_clock_form_with_company_uses_company_employee_queryset(self):
        company, _workplace = self.set_employee_context()
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        form = ManualTimeClockEntryForm(company=company)

        employees = form.fields['employee'].queryset
        self.assertIn(self.employee, employees)
        self.assertNotIn(other, employees)

    def test_manual_clock_form_with_company_rejects_other_company_employee(self):
        company, _workplace = self.set_employee_context()
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        form = ManualTimeClockEntryForm({
            'employee': other.pk,
            'entry_type': TimeClockEntry.EntryType.IN,
            'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'manual_reason': 'Fichaje introducido por administrador.',
        }, company=company)

        self.assertFalse(form.is_valid())
        self.assertIn('employee', form.errors)

    def test_manual_clock_form_without_company_rejects_employees(self):
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=Company.objects.create(name='Empresa B'),
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )

        form = ManualTimeClockEntryForm(company=None)

        employees = form.fields['employee'].queryset
        self.assertFalse(employees.exists())
        for employee in (self.employee, other):
            with self.subTest(employee=employee.pk):
                bound_form = ManualTimeClockEntryForm({
                    'employee': employee.pk,
                    'entry_type': TimeClockEntry.EntryType.IN,
                    'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                    'manual_reason': 'Fichaje sin contexto de empresa.',
                })
                self.assertFalse(bound_form.is_valid())
                self.assertIn('employee', bound_form.errors)

    def test_admin_with_company_cannot_create_manual_clock_for_other_company_employee(self):
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

        response = self.client.post(reverse('timeclock:manual-create'), {
            'employee': other.pk,
            'entry_type': TimeClockEntry.EntryType.IN,
            'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'manual_reason': 'Fichaje introducido por administrador.',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TimeClockEntry.objects.filter(employee=other).exists())

    def test_admin_manual_clock_saves_company_and_workplace(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('timeclock:manual-create'), {
            'employee': self.employee.pk,
            'entry_type': TimeClockEntry.EntryType.IN,
            'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'manual_reason': 'Fichaje introducido por administrador.',
        })

        self.assertRedirects(response, reverse('timeclock:history'))
        entry = TimeClockEntry.objects.get(status=TimeClockEntry.Status.MANUAL)
        self.assertEqual(entry.company, company)
        self.assertEqual(entry.workplace, workplace)

    def test_admin_can_correct_entry_with_audit_log(self):
        company, workplace = self.set_employee_context()
        self.employee.role = EmployeeProfile.Role.ADMIN
        self.employee.save(update_fields=['role'])
        entry = TimeClockEntry.objects.create(
            employee=self.employee,
            company=company,
            workplace=workplace,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('timeclock:correct', args=[entry.pk]), {
            'entry_type': TimeClockEntry.EntryType.OUT,
            'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'manual_reason': 'Se registró el tipo equivocado.',
        })

        self.assertRedirects(response, reverse('timeclock:history'))
        entry.refresh_from_db()
        self.assertEqual(entry.status, TimeClockEntry.Status.CORRECTED)
        self.assertEqual(entry.entry_type, TimeClockEntry.EntryType.OUT)
        self.assertEqual(entry.company, company)
        self.assertEqual(entry.workplace, workplace)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.CLOCK_CORRECTED).exists())

    def test_admin_with_company_cannot_correct_other_company_entry(self):
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
        entry = TimeClockEntry.objects.create(
            employee=other,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('timeclock:correct', args=[entry.pk]), {
            'entry_type': TimeClockEntry.EntryType.OUT,
            'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'manual_reason': 'Se registró el tipo equivocado.',
        })

        self.assertEqual(response.status_code, 404)
        entry.refresh_from_db()
        self.assertEqual(entry.status, TimeClockEntry.Status.VALID)
        self.assertEqual(entry.entry_type, TimeClockEntry.EntryType.IN)
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.CLOCK_CORRECTED).exists())

    def test_user_without_profile_cannot_correct_entry(self):
        user_without_profile = User.objects.create_user(username='sinperfil', password='secret')
        other_company = Company.objects.create(name='Empresa B')
        other_user = User.objects.create_user(username='luis', password='secret')
        other = EmployeeProfile.objects.create(
            user=other_user,
            company=other_company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        entry = TimeClockEntry.objects.create(
            employee=other,
            company=other_company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=other_user,
        )
        self.client.force_login(user_without_profile)

        response = self.client.post(reverse('timeclock:correct', args=[entry.pk]), {
            'entry_type': TimeClockEntry.EntryType.OUT,
            'timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
            'manual_reason': 'Se registró el tipo equivocado.',
        })

        self.assertEqual(response.status_code, 403)
        entry.refresh_from_db()
        self.assertEqual(entry.status, TimeClockEntry.Status.VALID)
        self.assertEqual(entry.entry_type, TimeClockEntry.EntryType.IN)

    def test_worker_cannot_correct_entry(self):
        entry = TimeClockEntry.objects.create(
            employee=self.employee,
            company=self.employee.company,
            entry_type=TimeClockEntry.EntryType.IN,
            timestamp=timezone.now(),
            status=TimeClockEntry.Status.VALID,
            created_by=self.user,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('timeclock:correct', args=[entry.pk]))

        self.assertEqual(response.status_code, 403)

# Create your tests here.
