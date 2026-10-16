from django.db import migrations


def backfill_payroll_company(apps, schema_editor):
    MonthlyHoursSummary = apps.get_model('payroll', 'MonthlyHoursSummary')
    PayrollDraft = apps.get_model('payroll', 'PayrollDraft')
    PayrollDraftLine = apps.get_model('payroll', 'PayrollDraftLine')

    summaries = []
    for summary in MonthlyHoursSummary.objects.filter(company__isnull=True).select_related('employee').iterator():
        if not summary.employee.company_id:
            continue
        summary.company_id = summary.employee.company_id
        summaries.append(summary)
    if summaries:
        MonthlyHoursSummary.objects.bulk_update(summaries, ['company'])

    lines = []
    queryset = PayrollDraftLine.objects.filter(company__isnull=True).select_related('employee', 'draft')
    for line in queryset.iterator():
        company_id = line.employee.company_id or line.draft.company_id
        if not company_id:
            continue
        line.company_id = company_id
        lines.append(line)
    if lines:
        PayrollDraftLine.objects.bulk_update(lines, ['company'])

    drafts = []
    for draft in PayrollDraft.objects.filter(company__isnull=True).iterator():
        company_ids = set(
            PayrollDraftLine.objects
            .filter(draft=draft, company__isnull=False)
            .values_list('company_id', flat=True)
            .distinct()
        )
        if len(company_ids) == 1:
            draft.company_id = company_ids.pop()
            drafts.append(draft)
    if drafts:
        PayrollDraft.objects.bulk_update(drafts, ['company'])


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0005_backfill_employeeprofile_company_workplace'),
        ('payroll', '0003_monthlyhourssummary_company_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_payroll_company, migrations.RunPython.noop),
    ]
