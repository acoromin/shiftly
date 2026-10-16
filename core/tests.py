from datetime import date, datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from audit.models import AuditLog
from companies.models import Company
from employees.models import EmployeeProfile

from .models import BusinessConfig


class MaintenanceModeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Empresa A')
        self.admin_user = User.objects.create_user(username='admin', password='secret')
        self.admin_profile = EmployeeProfile.objects.create(
            user=self.admin_user,
            company=self.company,
            full_name='Administradora',
            start_date=date(2026, 1, 1),
            role=EmployeeProfile.Role.ADMIN,
        )
        self.worker_user = User.objects.create_user(username='ana', password='secret')
        self.worker_profile = EmployeeProfile.objects.create(
            user=self.worker_user,
            company=self.company,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        self.config = BusinessConfig.get_solo()

    def test_worker_sees_maintenance_screen_when_enabled(self):
        self.config.maintenance_enabled = True
        self.config.save()
        self.client.force_login(self.worker_user)

        response = self.client.get(reverse('timeclock:scan'))

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'Estamos realizando tareas de mantenimiento', status_code=503)

    def test_admin_keeps_access_during_maintenance(self):
        self.config.maintenance_enabled = True
        self.config.save()
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modo mantenimiento activo')

    def test_scheduled_maintenance_is_active_inside_window(self):
        now = timezone.now()
        self.config.maintenance_scheduled_start = now - timedelta(minutes=5)
        self.config.maintenance_scheduled_end = now + timedelta(minutes=30)
        self.config.save()

        self.assertTrue(self.config.is_maintenance_active(now))
        self.assertFalse(self.config.is_maintenance_active(now + timedelta(hours=1)))

    def test_emergency_maintenance_can_be_enabled_outside_monday(self):
        friday = timezone.make_aware(datetime(2026, 6, 26, 18, 0))
        self.config.maintenance_enabled = True

        self.assertEqual(friday.weekday(), 4)
        self.assertTrue(self.config.is_maintenance_active(friday))

    def test_admin_activation_is_audited(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(reverse('core:settings'), {
            'name': 'Xarlot',
            'public_wifi_ip': '',
            'clock_tolerance_minutes': '5',
            'maintenance_enabled': '',
            'maintenance_scheduled_start': '',
            'maintenance_scheduled_end': '',
            'maintenance_reason': 'Actualización de seguridad',
            'maintenance_message': 'Aplicación temporalmente en mantenimiento.',
            'action': 'activate',
        })

        self.assertRedirects(response, reverse('core:settings'))
        self.config.refresh_from_db()
        self.assertTrue(self.config.maintenance_enabled)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.MAINTENANCE_ENABLED).exists()
        )

    def test_worker_cannot_open_configuration(self):
        self.client.force_login(self.worker_user)

        response = self.client.get(reverse('core:settings'))

        self.assertEqual(response.status_code, 403)
