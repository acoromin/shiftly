from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from companies.models import Company
from employees.models import EmployeeProfile

from .models import BusinessConfig


class ConfigurationAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company_a = Company.objects.create(name='Empresa A')
        cls.company_b = Company.objects.create(name='Empresa B')
        cls.admin_a = User.objects.create_user(username='admin-a')
        cls.admin_b = User.objects.create_user(username='admin-b')
        cls.worker_b = User.objects.create_user(username='worker-b')
        for user, company, role in (
            (cls.admin_a, cls.company_a, EmployeeProfile.Role.ADMIN),
            (cls.admin_b, cls.company_b, EmployeeProfile.Role.ADMIN),
            (cls.worker_b, cls.company_b, EmployeeProfile.Role.WORKER),
        ):
            EmployeeProfile.objects.create(
                user=user, company=company, role=role,
                full_name=user.username, start_date=date(2026, 1, 1),
            )
        cls.technician = User.objects.create_superuser(username='technician')
        cls.config = BusinessConfig.get_solo()

    def test_company_admin_cannot_activate_global_maintenance(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(reverse('core:settings'), {
            'name': 'Cambio global indebido', 'clock_tolerance_minutes': 99,
            'maintenance_message': 'Mensaje global indebido', 'action': 'activate',
        })
        self.assertEqual(response.status_code, 403)
        self.config.refresh_from_db()
        self.assertFalse(self.config.maintenance_enabled)
        self.assertFalse(AuditLog.objects.exists())
        self.client.force_login(self.worker_b)
        self.assertEqual(self.client.get(reverse('timeclock:scan')).status_code, 200)

    def test_global_get_and_post_denied_for_nontechnical_roles(self):
        staff = User.objects.create_user(username='staff', is_staff=True)
        unassigned = User.objects.create_user(username='unassigned')
        nonstaff_superuser = User.objects.create_user(username='nonstaff', is_superuser=True)
        original = BusinessConfig.objects.values().get(pk=1)
        for user in (self.admin_a, self.admin_b, self.worker_b, staff, unassigned, nonstaff_superuser):
            self.client.force_login(user)
            for method, data in [('get', {})] + [('post', {'action': action}) for action in ('activate', 'save', 'disable')]:
                with self.subTest(user=user.username, method=method, data=data):
                    response = getattr(self.client, method)(reverse('core:settings'), data)
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(BusinessConfig.objects.values().get(pk=1), original)
        self.assertFalse(AuditLog.objects.exists())

    def test_company_admin_cannot_disable_existing_global_maintenance(self):
        self.config.maintenance_enabled = True
        self.config.save()
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.post(reverse('core:settings'), {'action': 'disable'}).status_code, 403)
        self.config.refresh_from_db()
        self.assertTrue(self.config.maintenance_enabled)
        self.assertFalse(AuditLog.objects.exists())

    def test_denied_request_does_not_create_global_config(self):
        BusinessConfig.objects.all().delete()
        self.client.force_login(self.admin_a)
        self.assertEqual(self.client.get(reverse('core:settings')).status_code, 403)
        self.assertEqual(self.client.get(reverse('core:company-settings')).status_code, 200)
        self.assertFalse(BusinessConfig.objects.exists())

    def test_company_get_ignores_other_company_id(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse('core:company-settings'), {'company': self.company_b.pk})
        self.assertContains(response, 'Empresa A')
        self.assertNotContains(response, 'Empresa B')
        self.assertEqual(response.context['form'].instance.pk, self.company_a.pk)
        self.assertNotContains(response, f'href="{reverse("core:settings")}"')

    def test_company_update_is_scoped_and_cannot_set_platform_fields(self):
        self.client.force_login(self.admin_a)
        original_global = BusinessConfig.objects.values().get(pk=1)
        original_other = Company.objects.values().get(pk=self.company_b.pk)
        response = self.client.post(reverse('core:company-settings'), {
            'company': self.company_b.pk, 'id': self.company_b.pk,
            'name': 'Empresa A actualizada', 'clock_tolerance_minutes': 17,
            'maintenance_enabled': 'on', 'action': 'activate',
            'is_active': '', 'general_config': '{"unexpected": true}',
        })
        self.assertRedirects(response, reverse('core:company-settings'))
        self.company_a.refresh_from_db()
        self.assertEqual(self.company_a.name, 'Empresa A actualizada')
        self.assertEqual(self.company_a.clock_tolerance_minutes, 17)
        self.assertTrue(self.company_a.is_active)
        self.assertEqual(self.company_a.general_config, {})
        self.assertEqual(Company.objects.values().get(pk=self.company_b.pk), original_other)
        self.assertEqual(BusinessConfig.objects.values().get(pk=1), original_global)
        self.client.force_login(self.admin_b)
        response = self.client.get(reverse('core:company-settings'))
        self.assertContains(response, 'Empresa B')
        self.assertNotContains(response, 'Empresa A actualizada')
        self.client.force_login(self.worker_b)
        self.assertEqual(self.client.get(reverse('timeclock:scan')).status_code, 200)

    def test_company_settings_reject_invalid_tolerance(self):
        self.client.force_login(self.admin_a)
        for value in ('-1', '32768', 'invalid'):
            response = self.client.post(reverse('core:company-settings'), {'name': 'Changed', 'clock_tolerance_minutes': value})
            self.assertEqual(response.status_code, 200)
            self.assertIn('clock_tolerance_minutes', response.context['form'].errors)
        self.company_a.refresh_from_db()
        self.assertEqual(self.company_a.name, 'Empresa A')

    def test_company_settings_denied_without_active_company_admin(self):
        unassigned = User.objects.create_user(username='unassigned')
        for user in (self.worker_b, self.technician, unassigned):
            self.client.force_login(user)
            for method in ('get', 'post'):
                with self.subTest(user=user.username, method=method):
                    response = getattr(self.client, method)(reverse('core:company-settings'), {'name': 'Changed', 'clock_tolerance_minutes': 99})
                    self.assertEqual(response.status_code, 403)
        self.company_b.refresh_from_db()
        self.assertEqual(self.company_b.name, 'Empresa B')

    def test_inactive_profiles_cannot_access_or_write_client_routes(self):
        for user in (self.admin_a, self.worker_b):
            EmployeeProfile.objects.filter(user=user).update(is_active=False)
            self.client.force_login(user)
            for route in ('core:company-settings', 'core:settings', 'dashboard:index', 'timeclock:scan', 'leaves:create'):
                for method in ('get', 'post'):
                    with self.subTest(user=user.username, route=route, method=method):
                        self.assertEqual(getattr(self.client, method)(reverse(route)).status_code, 403)
            self.assertEqual(self.client.post(reverse('logout')).status_code, 302)

    def test_inactive_company_blocks_admin_and_worker(self):
        self.company_b.is_active = False
        self.company_b.save()
        for user in (self.admin_b, self.worker_b):
            self.client.force_login(user)
            for route in ('core:company-settings', 'dashboard:index', 'timeclock:scan'):
                self.assertEqual(self.client.get(reverse(route)).status_code, 403)
                self.assertEqual(self.client.post(reverse(route)).status_code, 403)

    def test_inactive_user_session_cannot_change_configuration(self):
        for user in (self.admin_a, self.technician):
            self.client.force_login(user)
            user.is_active = False
            user.save()
            for route in ('core:settings', 'core:company-settings'):
                self.assertEqual(self.client.post(reverse(route), {'action': 'activate'}).status_code, 302)
        self.config.refresh_from_db()
        self.assertFalse(self.config.maintenance_enabled)

    def test_missing_company_is_rejected_even_for_unsaved_legacy_profile(self):
        from django.core.exceptions import PermissionDenied
        from employees.permissions import require_company_admin
        self.admin_a.employee_profile.company = None
        with self.assertRaises(PermissionDenied):
            require_company_admin(self.admin_a)

    def test_technician_can_manage_maintenance_without_changing_company_config(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse('core:settings'))
        self.assertContains(response, 'Estos cambios afectan a todas las empresas.')
        self.assertNotContains(response, 'name="clock_tolerance_minutes"')
        company_before = list(Company.objects.order_by('pk').values())
        original_name = self.config.name
        original_tolerance = self.config.clock_tolerance_minutes
        response = self.client.post(reverse('core:settings'), {
            'action': 'activate', 'maintenance_message': 'Actualización',
            'name': 'Changed', 'clock_tolerance_minutes': 99,
        })
        self.assertRedirects(response, reverse('core:settings'))
        self.config.refresh_from_db()
        self.assertTrue(self.config.maintenance_enabled)
        self.assertEqual(self.config.updated_by, self.technician)
        self.assertEqual(self.config.name, original_name)
        self.assertEqual(self.config.clock_tolerance_minutes, original_tolerance)
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse('core:company-settings'))
        self.assertContains(response, 'Modo mantenimiento activo')
        self.assertNotContains(response, f'href="{reverse("core:settings")}"')
        self.client.force_login(self.worker_b)
        self.assertEqual(self.client.get(reverse('timeclock:scan')).status_code, 503)
        self.client.force_login(self.technician)
        self.assertRedirects(self.client.post(reverse('core:settings'), {'action': 'disable'}), reverse('core:settings'))
        self.config.refresh_from_db()
        self.assertFalse(self.config.maintenance_enabled)
        self.assertEqual(list(Company.objects.order_by('pk').values()), company_before)
        self.assertEqual(list(AuditLog.objects.order_by('pk').values_list('action', flat=True)), [AuditLog.Action.MAINTENANCE_ENABLED, AuditLog.Action.MAINTENANCE_DISABLED])

    def test_technician_can_schedule_and_clear_maintenance(self):
        self.client.force_login(self.technician)
        self.assertRedirects(self.client.post(reverse('core:settings'), {
            'action': 'save', 'maintenance_message': 'Actualización programada',
            'maintenance_scheduled_start': '2030-01-01T10:00',
            'maintenance_scheduled_end': '2030-01-01T11:00',
        }), reverse('core:settings'))
        self.config.refresh_from_db()
        self.assertIsNotNone(self.config.maintenance_scheduled_start)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.MAINTENANCE_SCHEDULED).exists())
        self.client.post(reverse('core:settings'), {'action': 'disable'})
        self.config.refresh_from_db()
        self.assertIsNone(self.config.maintenance_scheduled_start)
        self.assertIsNone(self.config.maintenance_scheduled_end)

    def test_technical_recovery_access_with_inactive_employee_profile(self):
        EmployeeProfile.objects.create(user=self.technician, company=self.company_a, full_name='Technical', start_date=date(2026, 1, 1), is_active=False)
        self.client.force_login(self.technician)
        self.assertEqual(self.client.get(reverse('core:settings')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:company-settings')).status_code, 403)

    def test_dashboard_uses_each_company_tolerance(self):
        from datetime import datetime, time
        from unittest.mock import patch
        from django.utils import timezone
        from scheduling.models import Shift
        from incidents.models import Incident

        self.company_a.clock_tolerance_minutes = 0
        self.company_a.save()
        self.company_b.clock_tolerance_minutes = 30
        self.company_b.save()
        for user, company in ((self.admin_a, self.company_a), (self.worker_b, self.company_b)):
            Shift.objects.create(employee=user.employee_profile, company=company,
                                 date=date(2026, 10, 22), start_time=time(10), end_time=time(18),
                                 created_by=user)
        now = timezone.make_aware(datetime(2026, 10, 22, 10, 10))
        with patch('django.utils.timezone.now', return_value=now):
            self.client.force_login(self.admin_a)
            self.assertEqual(self.client.get(reverse('dashboard:index')).status_code, 200)
            self.client.force_login(self.admin_b)
            self.assertEqual(self.client.get(reverse('dashboard:index')).status_code, 200)
        self.assertTrue(Incident.objects.filter(company=self.company_a, incident_type=Incident.IncidentType.MISSING_CLOCK_IN).exists())
        self.assertFalse(Incident.objects.filter(company=self.company_b).exists())
