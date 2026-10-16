import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def validate_line_company(apps, schema_editor):
    Line = apps.get_model('payroll', 'PayrollDraftLine')
    lines = Line.objects.using(schema_editor.connection.alias)
    checks = {
        'company_null': lines.filter(company__isnull=True).count(),
        'employee_company_mismatch': lines.filter(company__isnull=False).exclude(
            company_id=F('employee__company_id'),
        ).count(),
        'draft_company_mismatch': lines.filter(company__isnull=False).exclude(
            company_id=F('draft__company_id'),
        ).count(),
    }
    failures = ', '.join(f'{name}={count}' for name, count in checks.items() if count)
    if failures:
        raise RuntimeError(f'PayrollDraftLine: {failures}. Audita y sanea las lineas antes de migrar.')


class Migration(migrations.Migration):
    dependencies = [('payroll', '0006_alter_payrolldraft_company')]
    operations = [
        migrations.RunPython(validate_line_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='payrolldraftline', name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name='payroll_draft_lines',
                to='companies.company', verbose_name='empresa',
            ),
        ),
    ]
