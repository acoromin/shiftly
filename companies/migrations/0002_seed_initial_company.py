from django.db import migrations


def seed_initial_company(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    Workplace = apps.get_model('companies', 'Workplace')
    JobPosition = apps.get_model('companies', 'JobPosition')
    BusinessConfig = apps.get_model('core', 'BusinessConfig')

    config = BusinessConfig.objects.order_by('pk').first()
    company_name = (config.name or '').strip() if config else ''
    if not company_name:
        company_name = 'Xarlot'

    company, _ = Company.objects.get_or_create(
        name=company_name,
        defaults={'business_type': 'bar'},
    )

    workplace, created = Workplace.objects.get_or_create(
        company=company,
        name='Centro principal',
        defaults={
            'public_wifi_ip': config.public_wifi_ip if config else None,
            'qr_token_hash': config.qr_static_token_hash if config else '',
        },
    )

    if config and not created:
        update_fields = []
        if config.public_wifi_ip and not workplace.public_wifi_ip:
            workplace.public_wifi_ip = config.public_wifi_ip
            update_fields.append('public_wifi_ip')
        if config.qr_static_token_hash and not workplace.qr_token_hash:
            workplace.qr_token_hash = config.qr_static_token_hash
            update_fields.append('qr_token_hash')
        if update_fields:
            workplace.save(update_fields=update_fields)

    for position_name in ['Camarero', 'Cocinero']:
        JobPosition.objects.get_or_create(company=company, name=position_name)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_businessconfig_maintenance_enabled_and_more'),
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_initial_company, migrations.RunPython.noop),
    ]
