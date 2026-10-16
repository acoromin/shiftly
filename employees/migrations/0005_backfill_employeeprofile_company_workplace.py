from django.db import migrations


def backfill_employeeprofile_company_workplace(apps, schema_editor):
    EmployeeProfile = apps.get_model('employees', 'EmployeeProfile')
    Company = apps.get_model('companies', 'Company')
    Workplace = apps.get_model('companies', 'Workplace')

    company = Company.objects.filter(name='Xarlot').first()
    if not company:
        company = Company.objects.filter(is_active=True).order_by('name', 'pk').first()
    if not company:
        return

    workplace = Workplace.objects.filter(company=company, name='Centro principal').first()
    if not workplace:
        workplace = Workplace.objects.filter(company=company, is_active=True).order_by('name', 'pk').first()

    updates = {'company': company}
    if workplace:
        updates['primary_workplace'] = workplace

    EmployeeProfile.objects.filter(company__isnull=True).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0004_employeeprofile_company_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_employeeprofile_company_workplace, migrations.RunPython.noop),
    ]
