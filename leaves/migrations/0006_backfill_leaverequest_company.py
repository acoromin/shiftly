from django.db import migrations


def backfill_leaverequest_company(apps, schema_editor):
    LeaveRequest = apps.get_model('leaves', 'LeaveRequest')

    leave_requests = []
    for leave_request in LeaveRequest.objects.filter(company__isnull=True).select_related('employee').iterator():
        if not leave_request.employee.company_id:
            continue
        leave_request.company_id = leave_request.employee.company_id
        leave_requests.append(leave_request)

    if leave_requests:
        LeaveRequest.objects.bulk_update(leave_requests, ['company'])


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0005_backfill_employeeprofile_company_workplace'),
        ('leaves', '0005_leaverequest_company'),
    ]

    operations = [
        migrations.RunPython(backfill_leaverequest_company, migrations.RunPython.noop),
    ]
