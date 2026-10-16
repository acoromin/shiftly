from django.db import migrations


def backfill_shift_company_workplace(apps, schema_editor):
    Shift = apps.get_model('scheduling', 'Shift')

    shifts = []
    for shift in Shift.objects.filter(company__isnull=True).select_related('employee').iterator():
        if not shift.employee.company_id:
            continue
        shift.company_id = shift.employee.company_id
        if shift.employee.primary_workplace_id:
            shift.workplace_id = shift.employee.primary_workplace_id
        shifts.append(shift)

    if shifts:
        Shift.objects.bulk_update(shifts, ['company', 'workplace'])


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0005_backfill_employeeprofile_company_workplace'),
        ('scheduling', '0005_shift_company_shift_workplace'),
    ]

    operations = [
        migrations.RunPython(backfill_shift_company_workplace, migrations.RunPython.noop),
    ]
