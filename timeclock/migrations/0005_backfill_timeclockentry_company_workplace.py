from django.db import migrations


def backfill_timeclockentry_company_workplace(apps, schema_editor):
    TimeClockEntry = apps.get_model('timeclock', 'TimeClockEntry')

    entries = []
    queryset = TimeClockEntry.objects.filter(company__isnull=True).select_related(
        'employee',
        'employee__primary_workplace',
        'related_shift',
        'related_shift__workplace',
    )
    for entry in queryset.iterator():
        if not entry.employee.company_id:
            continue

        company_id = entry.employee.company_id
        workplace_id = None
        if (
            entry.related_shift_id
            and entry.related_shift.workplace_id
            and entry.related_shift.workplace.company_id == company_id
        ):
            workplace_id = entry.related_shift.workplace_id
        elif (
            entry.employee.primary_workplace_id
            and entry.employee.primary_workplace.company_id == company_id
        ):
            workplace_id = entry.employee.primary_workplace_id

        entry.company_id = company_id
        if workplace_id:
            entry.workplace_id = workplace_id
        entries.append(entry)

    if entries:
        TimeClockEntry.objects.bulk_update(entries, ['company', 'workplace'])


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0005_backfill_employeeprofile_company_workplace'),
        ('scheduling', '0006_backfill_shift_company_workplace'),
        ('timeclock', '0004_timeclockentry_company_timeclockentry_workplace'),
    ]

    operations = [
        migrations.RunPython(backfill_timeclockentry_company_workplace, migrations.RunPython.noop),
    ]
