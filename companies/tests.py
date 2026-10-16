from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Company, JobPosition, Workplace


class CompanyModelTests(TestCase):
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
