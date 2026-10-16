import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def validate_company_integrity(apps, schema_editor):
    TimeClockEntry = apps.get_model('timeclock', 'TimeClockEntry')
    entries = TimeClockEntry.objects.using(schema_editor.connection.alias)
    checks = {
        'company_null': entries.filter(company__isnull=True).count(),
        'employee_company_mismatch': entries.filter(company__isnull=False).exclude(
            company_id=F('employee__company_id'),
        ).count(),
        'workplace_company_mismatch': entries.filter(workplace__isnull=False).exclude(
            company_id=F('workplace__company_id'),
        ).count(),
        'related_shift_company_mismatch': entries.filter(related_shift__isnull=False).exclude(
            company_id=F('related_shift__company_id'),
        ).count(),
        'related_shift_employee_mismatch': entries.filter(related_shift__isnull=False).exclude(
            employee_id=F('related_shift__employee_id'),
        ).count(),
    }
    failures = ', '.join(f'{name}={count}' for name, count in checks.items() if count)
    if failures:
        raise RuntimeError(
            f'No se puede endurecer TimeClockEntry.company: {failures}. '
            'Audita y sanea los fichajes antes de volver a ejecutar la migracion.'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0006_alter_employeeprofile_company'),
        ('scheduling', '0007_alter_shift_company'),
        ('incidents', '0007_alter_incident_company'),
        ('timeclock', '0005_backfill_timeclockentry_company_workplace'),
    ]

    operations = [
        migrations.RunPython(validate_company_integrity, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='timeclockentry',
            name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='timeclock_entries',
                to='companies.company',
                verbose_name='empresa',
            ),
        ),
    ]
