import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F


def validate_draft_company(apps, schema_editor):
    Draft = apps.get_model('payroll', 'PayrollDraft')
    Line = apps.get_model('payroll', 'PayrollDraftLine')
    alias = schema_editor.connection.alias
    drafts = Draft.objects.using(alias)
    lines = Line.objects.using(alias)
    checks = {
        'company_null': drafts.filter(company__isnull=True).count(),
        'line_draft_company_mismatch': lines.filter(company__isnull=False).exclude(
            company_id=F('draft__company_id'),
        ).count(),
        'employee_draft_company_mismatch': lines.exclude(
            employee__company_id=F('draft__company_id'),
        ).count(),
    }
    failures = ', '.join(f'{name}={count}' for name, count in checks.items() if count)
    if failures:
        raise RuntimeError(f'PayrollDraft: {failures}. Audita y sanea los borradores antes de migrar.')


class Migration(migrations.Migration):
    dependencies = [('payroll', '0005_alter_monthlyhourssummary_company')]
    operations = [
        migrations.RunPython(validate_draft_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='payrolldraft', name='company',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name='payroll_drafts',
                to='companies.company', verbose_name='empresa',
            ),
        ),
    ]
