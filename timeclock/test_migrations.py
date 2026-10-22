from datetime import date, time
from importlib import import_module

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase
from django.utils import timezone


class TimeClockCompanyMigrationTests(TransactionTestCase):
    migrate_from = ('timeclock', '0005_backfill_timeclockentry_company_workplace')
    migrate_to = ('timeclock', '0006_alter_timeclockentry_company')

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        executor.migrate([self.migrate_from])
        # Other apps keep their applied schemas while timeclock is rolled back.
        targets = [target for target in self.latest_targets if target[0] != 'timeclock']
        self.apps = executor.loader.project_state(targets + [self.migrate_from]).apps
        self.Entry = self.apps.get_model('timeclock', 'TimeClockEntry')
        self.addCleanup(self.restore_schema)
        Company = self.apps.get_model('companies', 'Company')
        Workplace = self.apps.get_model('companies', 'Workplace')
        User = self.apps.get_model('auth', 'User')
        Employee = self.apps.get_model('employees', 'EmployeeProfile')
        Shift = self.apps.get_model('scheduling', 'Shift')
        self.company = Company.objects.create(name='Empresa A')
        self.other_company = Company.objects.create(name='Empresa B')
        self.workplace = Workplace.objects.create(company=self.company, name='Centro empleado')
        self.shift_workplace = Workplace.objects.create(company=self.company, name='Centro turno')
        self.other_workplace = Workplace.objects.create(company=self.other_company, name='Centro B')
        self.user = User.objects.create(username='ana')
        self.employee = Employee.objects.create(
            user=self.user,
            company=self.company,
            primary_workplace=self.workplace,
            full_name='Ana Garcia',
            start_date=date(2026, 1, 1),
        )
        other_user = User.objects.create(username='luis')
        self.other_employee = Employee.objects.create(
            user=other_user,
            company=self.company,
            full_name='Luis Perez',
            start_date=date(2026, 1, 1),
        )
        self.shift = Shift.objects.create(
            employee=self.employee,
            company=self.company,
            workplace=self.shift_workplace,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )
        self.other_shift = Shift.objects.create(
            employee=self.other_employee,
            company=self.company,
            date=date(2026, 6, 23),
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

    def restore_schema(self):
        # Invalid legacy rows must not block schema restoration after a failed test.
        self.Entry.objects.all().delete()
        MigrationExecutor(connection).migrate(self.latest_targets)

    def create_entry(self, **overrides):
        values = {
            'employee': self.employee,
            'company': self.company,
            'entry_type': 'in',
            'timestamp': timezone.now(),
            'created_by': self.user,
        }
        values.update(overrides)
        return self.Entry.objects.create(**values)

    def test_historical_backfill_and_new_migration_preserve_entries(self):
        own_entry = self.create_entry(company=None)
        shift_entry = self.create_entry(company=None, related_shift=self.shift)
        without_workplace = self.create_entry()
        migration = import_module('timeclock.migrations.0005_backfill_timeclockentry_company_workplace')

        with connection.schema_editor() as editor:
            migration.backfill_timeclockentry_company_workplace(self.apps, editor)
        MigrationExecutor(connection).migrate([self.migrate_to])

        for entry, workplace_id in (
            (own_entry, self.workplace.pk),
            (shift_entry, self.shift_workplace.pk),
            (without_workplace, None),
        ):
            with self.subTest(entry=entry.pk):
                entry.refresh_from_db()
                self.assertEqual(entry.company_id, self.company.pk)
                self.assertEqual(entry.workplace_id, workplace_id)
        self.assertEqual(self.Entry.objects.count(), 3)
        with connection.cursor() as cursor:
            fields = {
                field.name: field
                for field in connection.introspection.get_table_description(cursor, self.Entry._meta.db_table)
            }
        self.assertFalse(fields['company_id'].null_ok)
        self.assertTrue(fields['workplace_id'].null_ok)

    def test_migration_blocks_inconsistent_data_before_changing_schema(self):
        cases = (
            ({'company': None}, 'company_null=1'),
            ({'company': self.other_company}, 'employee_company_mismatch=1'),
            ({'workplace': self.other_workplace}, 'workplace_company_mismatch=1'),
            ({'company': self.other_company, 'related_shift': self.shift}, 'related_shift_company_mismatch=1'),
            ({'related_shift': self.other_shift}, 'related_shift_employee_mismatch=1'),
        )
        for values, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                entry = self.create_entry(**values)
                with self.assertRaisesMessage(RuntimeError, expected_error):
                    MigrationExecutor(connection).migrate([self.migrate_to])
                self.assertNotIn(self.migrate_to, MigrationRecorder(connection).applied_migrations())
                with connection.cursor() as cursor:
                    fields = {
                        field.name: field
                        for field in connection.introspection.get_table_description(cursor, self.Entry._meta.db_table)
                    }
                self.assertTrue(fields['company_id'].null_ok)
                entry.refresh_from_db()
                expected_company = values.get('company', self.company)
                self.assertEqual(entry.company_id, expected_company.pk if expected_company else None)
                entry.delete()
