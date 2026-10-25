from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from companies.models import Company
from employees.models import EmployeeProfile
from scheduling.models import Shift
from timeclock.models import TimeClockEntry


class LocalDemoTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_creates_usable_roles_without_changing_existing_technical_user(self):
        technician = get_user_model().objects.create_superuser(username='technical')
        with TemporaryDirectory() as temporary:
            access_file = Path(temporary) / 'demo-access.txt'
            with patch('core.management.commands.seed_local_demo.ACCESS_FILE', access_file):
                call_command('seed_local_demo', stdout=StringIO())
                call_command('seed_local_demo', stdout=StringIO())
            password = access_file.read_text().split('Contraseña para los tres: ')[1].splitlines()[0]
            self.assertEqual(access_file.stat().st_mode & 0o777, 0o600)

        technician.refresh_from_db()
        self.assertTrue(technician.is_superuser)
        self.assertFalse(EmployeeProfile.objects.filter(user=technician).exists())
        self.assertEqual(Shift.objects.count(), 14)
        self.assertTrue(Company.objects.filter(name='Café Brisa', business_type=Company.BusinessType.CAFE).exists())
        self.assertTrue(Company.objects.filter(name='Xarlot').exists())
        self.assertTrue(TimeClockEntry.objects.exists())
        self.assertTrue(self.client.login(username='demo_admin', password=password))
        self.assertEqual(self.client.get(reverse('dashboard:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('employees:list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:company-settings')).status_code, 200)
        self.client.logout()
        self.assertTrue(self.client.login(username='demo_ana', password=password))
        self.assertEqual(self.client.get(reverse('dashboard:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('employees:list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('timeclock:history')).status_code, 200)
