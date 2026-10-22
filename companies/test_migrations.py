from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CompanyToleranceMigrationTests(TransactionTestCase):
    migrate_from = ('companies', '0003_copy_legacy_clock_credentials')
    migrate_to = ('companies', '0004_company_clock_tolerance')

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_schema)
        executor.migrate([self.migrate_from])
        targets = [node for node in self.latest_targets if node[0] != 'companies']
        apps = executor.loader.project_state(targets + [self.migrate_from]).apps
        self.Company = apps.get_model('companies', 'Company')
        self.Config = apps.get_model('core', 'BusinessConfig')

    def restore_schema(self):
        MigrationExecutor(connection).migrate(self.latest_targets)

    def migrate(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        return executor.loader.project_state(self.latest_targets).apps.get_model('companies', 'Company')

    def test_preserves_global_tolerance_for_all_existing_companies(self):
        self.Config.objects.create(pk=1, name='Legacy', clock_tolerance_minutes=19)
        a = self.Company.objects.create(name='Empresa A')
        b = self.Company.objects.create(name='Empresa B', is_active=False)
        Company = self.migrate()
        self.assertEqual(Company.objects.get(pk=a.pk).clock_tolerance_minutes, 19)
        self.assertEqual(Company.objects.get(pk=b.pk).clock_tolerance_minutes, 19)
        self.assertEqual(Company.objects.get(pk=a.pk).name, 'Empresa A')
        self.assertFalse(Company.objects.get(pk=b.pk).is_active)
        self.assertEqual(Company.objects.create(name='Nueva').clock_tolerance_minutes, 5)
        self.assertEqual(self.Config.objects.get(pk=1).clock_tolerance_minutes, 19)

    def test_without_global_config_preserves_default_and_does_not_create_it(self):
        a = self.Company.objects.create(name='Empresa A')
        Company = self.migrate()
        self.assertEqual(Company.objects.get(pk=a.pk).clock_tolerance_minutes, 5)
        self.assertFalse(self.Config.objects.exists())
