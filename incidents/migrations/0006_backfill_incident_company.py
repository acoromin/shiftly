from django.db import migrations


def backfill_incident_company(apps, schema_editor):
    Incident = apps.get_model('incidents', 'Incident')

    incidents = []
    queryset = Incident.objects.filter(company__isnull=True).select_related(
        'employee',
        'shift',
        'timeclock_entry',
    )
    for incident in queryset.iterator():
        company_id = None
        if incident.employee.company_id:
            company_id = incident.employee.company_id
        elif incident.shift_id and incident.shift.company_id:
            company_id = incident.shift.company_id
        elif incident.timeclock_entry_id and incident.timeclock_entry.company_id:
            company_id = incident.timeclock_entry.company_id

        if not company_id:
            continue
        incident.company_id = company_id
        incidents.append(incident)

    if incidents:
        Incident.objects.bulk_update(incidents, ['company'])


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0005_backfill_employeeprofile_company_workplace'),
        ('scheduling', '0006_backfill_shift_company_workplace'),
        ('timeclock', '0005_backfill_timeclockentry_company_workplace'),
        ('incidents', '0005_incident_company'),
    ]

    operations = [
        migrations.RunPython(backfill_incident_company, migrations.RunPython.noop),
    ]
