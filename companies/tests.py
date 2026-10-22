from importlib import import_module
from io import StringIO

from django.apps import apps
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Company, JobPosition, Workplace
from core.models import BusinessConfig


class CompanyModelTests(TestCase):
    def test_technical_admin_can_generate_workplace_qr(self):
        workplace = Workplace.objects.get(company__name='Xarlot')
        technician = User.objects.create_superuser(username='technician', password='secret')
        self.client.force_login(technician)

        response = self.client.post(reverse('admin:companies_workplace_changelist'), {
            'action': 'generate_qr', '_selected_action': workplace.pk,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        workplace.refresh_from_db()
        self.assertTrue(workplace.qr_token_hash)
        self.assertContains(response, '/fichar/?token=')

    def test_clock_setup_configures_only_selected_workplace(self):
        company = Company.objects.get(name='Xarlot')
        selected = Workplace.objects.get(company=company)
        other = Workplace.objects.create(company=company, name='Centro B')
        output = StringIO()

        call_command('setup_xarlot_clock', workplace_id=selected.pk, wifi_ip='203.0.113.10',
                     base_url='https://example.test', stdout=output)

        selected.refresh_from_db()
        self.assertEqual(selected.public_wifi_ip, '203.0.113.10')
        token = output.getvalue().split('token=')[1].strip()
        self.assertTrue(selected.check_qr_token(token))
        self.assertFalse(other.check_qr_token(token))
        self.assertIn('https://example.test/fichar/?token=', output.getvalue())

    def test_legacy_credentials_copy_only_to_single_workplace(self):
        config = BusinessConfig.get_solo()
        config.public_wifi_ip = '203.0.113.10'
        config.set_qr_token('legacy-token')
        config.save()
        workplace = Workplace.objects.get(company__name='Xarlot')
        migration = import_module('companies.migrations.0003_copy_legacy_clock_credentials')

        migration.copy_legacy_clock_credentials(apps, connection.schema_editor())
        workplace.refresh_from_db()
        self.assertEqual(workplace.public_wifi_ip, config.public_wifi_ip)
        self.assertTrue(workplace.check_qr_token('legacy-token'))

        workplace.public_wifi_ip = None
        workplace.qr_token_hash = ''
        workplace.save(update_fields=['public_wifi_ip', 'qr_token_hash'])
        Workplace.objects.create(company=workplace.company, name='Centro B')
        migration.copy_legacy_clock_credentials(apps, connection.schema_editor())
        workplace.refresh_from_db()
        self.assertIsNone(workplace.public_wifi_ip)
        self.assertEqual(workplace.qr_token_hash, '')

    def test_initial_company_seed_exists(self):
        company = Company.objects.get(name='Xarlot')

        self.assertEqual(company.business_type, Company.BusinessType.BAR)
        self.assertTrue(Workplace.objects.filter(company=company, name='Centro principal').exists())
        self.assertTrue(JobPosition.objects.filter(company=company, name='Camarero').exists())
        self.assertTrue(JobPosition.objects.filter(company=company, name='Cocinero').exists())

    def test_company_string_uses_name(self):
        company = Company.objects.create(name='Xarlot', business_type=Company.BusinessType.BAR)

        self.assertEqual(str(company), 'Xarlot')
        self.assertTrue(company.is_active)

    def test_workplace_qr_token_is_checked_against_hash(self):
        company = Company.objects.create(name='Xarlot')
        workplace = Workplace.objects.create(company=company, name='Centro principal')

        workplace.set_qr_token('token-valido')
        workplace.save(update_fields=['qr_token_hash'])

        self.assertTrue(workplace.check_qr_token('token-valido'))
        self.assertFalse(workplace.check_qr_token('token-incorrecto'))

    def test_workplace_name_is_unique_per_company(self):
        company = Company.objects.create(name='Xarlot')
        other_company = Company.objects.create(name='Otra empresa')
        Workplace.objects.create(company=company, name='Centro principal')
        Workplace.objects.create(company=other_company, name='Centro principal')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Workplace.objects.create(company=company, name='Centro principal')

    def test_job_position_name_is_unique_per_company(self):
        company = Company.objects.create(name='Xarlot')
        other_company = Company.objects.create(name='Otra empresa')
        JobPosition.objects.create(company=company, name='Camarero')
        JobPosition.objects.create(company=other_company, name='Camarero')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JobPosition.objects.create(company=company, name='Camarero')
