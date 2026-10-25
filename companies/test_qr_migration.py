from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class WorkplacePublicIdMigrationTests(TransactionTestCase):
    migrate_from = ('companies', '0004_company_clock_tolerance')
    migrate_to = ('companies', '0005_workplace_qr_public_id')

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_schema)
        executor.migrate([self.migrate_from])
        targets = [target for target in self.latest_targets if target[0] != 'companies']
        apps = executor.loader.project_state(targets + [self.migrate_from]).apps
        self.Company = apps.get_model('companies', 'Company')
        self.Workplace = apps.get_model('companies', 'Workplace')

    def restore_schema(self):
        MigrationExecutor(connection).migrate(self.latest_targets)

    def test_backfill_gives_each_existing_center_a_distinct_public_id(self):
        company = self.Company.objects.create(name='Empresa A')
        first = self.Workplace.objects.create(company=company, name='Centro A', qr_token_hash='legacy-hash')
        second = self.Workplace.objects.create(company=company, name='Centro B', is_active=False)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        Workplace = executor.loader.project_state(self.latest_targets).apps.get_model('companies', 'Workplace')
        migrated = list(Workplace.objects.filter(pk__in=[first.pk, second.pk]).order_by('pk'))
        self.assertEqual(len({center.qr_public_id for center in migrated}), 2)
        self.assertTrue(all(center.qr_public_id for center in migrated))
        self.assertEqual(migrated[0].qr_token_hash, 'legacy-hash')
        self.assertFalse(migrated[1].is_active)
        self.assertNotIn(Workplace.objects.create(company_id=company.pk, name='Nuevo').qr_public_id,
                         {center.qr_public_id for center in migrated})
