import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def validate_summary_company(apps, schema_editor):
    Summary = apps.get_model('payroll', 'MonthlyHoursSummary')
    summaries = Summary.objects.using(schema_editor.connection.alias)
    nulls = summaries.filter(company__isnull=True).count()
    mismatches = summaries.filter(company__isnull=False).exclude(company_id=F('employee__company_id')).count()
    if nulls or mismatches:
        raise RuntimeError(
            f'MonthlyHoursSummary: company_null={nulls}, employee_company_mismatch={mismatches}. '
            'Audita y sanea los resumenes antes de migrar.'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('payroll', '0004_backfill_payroll_company'),
        ('timeclock', '0006_alter_timeclockentry_company'),
    ]
    operations = [
        migrations.RunPython(validate_summary_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='monthlyhourssummary', name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name='monthly_summaries',
                to='companies.company', verbose_name='empresa',
            ),
        ),
    ]
