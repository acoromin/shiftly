from datetime import date

from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from companies.models import Company, Workplace
from employees.models import EmployeeProfile

from .models import BusinessConfig


class TechnicalAdminAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name='Empresa A')
        cls.other_company = Company.objects.create(name='Empresa B')
        cls.staff = User.objects.create_user(username='company-admin', password='secret', is_staff=True)
        cls.staff.user_permissions.set(Permission.objects.all())
        EmployeeProfile.objects.create(
            user=cls.staff, company=cls.company, full_name='Admin empresa A',
            role=EmployeeProfile.Role.ADMIN, start_date=date(2026, 1, 1),
        )
        cls.other = EmployeeProfile.objects.create(
            user=User.objects.create_user(username='other'), company=cls.other_company,
            full_name='Empleado privado B', start_date=date(2026, 1, 1),
        )
        cls.technician = User.objects.create_superuser(username='technician', password='secret')

    def assert_admin_login_redirect(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('admin:login')))

    def test_staff_with_all_permissions_cannot_read_or_write_registered_models(self):
        self.client.force_login(self.staff)
        for model in admin.site._registry:
            prefix = f'admin:{model._meta.app_label}_{model._meta.model_name}'
            for action in ('changelist', 'add', 'change', 'delete', 'history'):
                args = [self.other.pk] if action in ('change', 'delete', 'history') else []
                url = reverse(f'{prefix}_{action}', args=args)
                with self.subTest(model=model.__name__, action=action):
                    self.assert_admin_login_redirect(self.client.get(url))
                    if action in ('add', 'change', 'delete'):
                        self.assert_admin_login_redirect(self.client.post(url, {'post': 'yes'}))
        self.other.refresh_from_db()
        self.assertEqual(self.other.company, self.other_company)

    def test_staff_without_profile_cannot_open_admin(self):
        staff = User.objects.create_user(username='unassigned-staff', is_staff=True)
        self.client.force_login(staff)
        self.assert_admin_login_redirect(self.client.get(reverse('admin:index')))

    def test_staff_cannot_query_autocomplete_or_generate_workplace_qr(self):
        workplace = Workplace.objects.create(company=self.company, name='Centro')
        old_hash = workplace.qr_token_hash
        self.client.force_login(self.staff)
        self.assert_admin_login_redirect(self.client.get(reverse('admin:autocomplete'), {
            'app_label': 'employees', 'model_name': 'employeeprofile', 'field_name': 'company', 'term': 'Empresa',
        }))
        self.assert_admin_login_redirect(self.client.post(reverse('admin:companies_workplace_changelist'), {
            'action': 'generate_qr', '_selected_action': workplace.pk,
        }))
        workplace.refresh_from_db()
        self.assertEqual(workplace.qr_token_hash, old_hash)

    def test_staff_login_is_rejected_with_clear_error(self):
        response = self.client.post(reverse('admin:login'), {
            'username': self.staff.username, 'password': 'secret', 'next': reverse('admin:index'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reservado a superusuarios tecnicos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_technical_superuser_can_login_and_see_global_admin(self):
        response = self.client.post(reverse('admin:login'), {
            'username': self.technician.username, 'password': 'secret', 'next': reverse('admin:index'),
        })
        self.assertRedirects(response, reverse('admin:index'))
        response = self.client.get(reverse('admin:employees_employeeprofile_changelist'))
        self.assertContains(response, self.other.full_name)
        response = self.client.get(reverse('admin:autocomplete'), {
            'app_label': 'employees', 'model_name': 'employeeprofile', 'field_name': 'company', 'term': 'Empresa B',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()['results']], [str(self.other_company.pk)])

    def test_company_admin_keeps_customer_access_scoped_to_company(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('employees:list'))
        self.assertContains(response, 'Admin empresa A')
        self.assertNotContains(response, self.other.full_name)

    def test_site_permission_requires_active_staff_superuser(self):
        request = RequestFactory().get('/administracion/')
        for active, staff, superuser in ((True, True, True), (True, True, False), (False, True, True), (True, False, True)):
            with self.subTest(active=active, staff=staff, superuser=superuser):
                request.user = User(is_active=active, is_staff=staff, is_superuser=superuser)
                self.assertEqual(admin.site.has_permission(request), active and staff and superuser)
