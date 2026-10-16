from datetime import date
from importlib import import_module

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


class PayrollMigrationTestCase(TransactionTestCase):
    """Exercise historical schemas and always restore the current schema."""

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        executor.migrate([self.migrate_from])
        targets = [target for target in self.latest_targets if target[0] != 'payroll']
        self.apps = executor.loader.project_state(targets + [self.migrate_from]).apps
        self.Summary = self.apps.get_model('payroll', 'MonthlyHoursSummary')
        self.Draft = self.apps.get_model('payroll', 'PayrollDraft')
        self.Line = self.apps.get_model('payroll', 'PayrollDraftLine')
        self.addCleanup(self.restore_schema)
        Company = self.apps.get_model('companies', 'Company')
        User = self.apps.get_model('auth', 'User')
        Employee = self.apps.get_model('employees', 'EmployeeProfile')
        self.company = Company.objects.create(name='Empresa A')
        self.other_company = Company.objects.create(name='Empresa B')
        self.user = User.objects.create(username='ana')
        self.employee = Employee.objects.create(
            user=self.user, company=self.company, full_name='Ana Garcia', start_date=date(2026, 1, 1),
        )

    def restore_schema(self):
        self.Line.objects.all().delete()
        self.Summary.objects.all().delete()
        self.Draft.objects.all().delete()
        MigrationExecutor(connection).migrate(self.latest_targets)

    def company_nullable(self, model):
        with connection.cursor() as cursor:
            fields = connection.introspection.get_table_description(cursor, model._meta.db_table)
        return next(field.null_ok for field in fields if field.name == 'company_id')

    def assert_migration_blocked(self, expected_error):
        with self.assertRaisesMessage(RuntimeError, expected_error):
            MigrationExecutor(connection).migrate([self.migrate_to])
        self.assertNotIn(self.migrate_to, MigrationRecorder(connection).applied_migrations())


class MonthlySummaryCompanyMigrationTests(PayrollMigrationTestCase):
    migrate_from = ('payroll', '0004_backfill_payroll_company')
    migrate_to = ('payroll', '0005_alter_monthlyhourssummary_company')

    def test_historical_backfill_and_migration_preserve_payroll(self):
        summary = self.Summary.objects.create(employee=self.employee, year=2026, month=6)
        draft = self.Draft.objects.create(year=2026, month=6, generated_by=self.user)
        line = self.Line.objects.create(draft=draft, employee=self.employee)
        migration = import_module('payroll.migrations.0004_backfill_payroll_company')
        with connection.schema_editor() as editor:
            migration.backfill_payroll_company(self.apps, editor)
        MigrationExecutor(connection).migrate([self.migrate_to])
        for obj in (summary, draft, line):
            obj.refresh_from_db()
            self.assertEqual(obj.company_id, self.company.pk)
        self.assertFalse(self.company_nullable(self.Summary))
        self.assertTrue(self.company_nullable(self.Draft))
        self.assertTrue(self.company_nullable(self.Line))

    def test_migration_rejects_null_and_mismatched_company(self):
        for company, message in ((None, 'company_null=1'), (self.other_company, 'employee_company_mismatch=1')):
            with self.subTest(company=company):
                summary = self.Summary.objects.create(employee=self.employee, company=company, year=2026, month=6)
                self.assert_migration_blocked(message)
                self.assertTrue(self.company_nullable(self.Summary))
                summary.delete()
