from django.db import migrations


def copy_legacy_clock_credentials(apps, schema_editor):
    BusinessConfig = apps.get_model('core', 'BusinessConfig')
    Workplace = apps.get_model('companies', 'Workplace')
    config = BusinessConfig.objects.filter(pk=1).first()
    if not config or not (config.qr_static_token_hash or config.public_wifi_ip):
        return

    # A global credential has no unambiguous destination when several centres exist.
    workplaces = list(Workplace.objects.all()[:2])
    if len(workplaces) != 1:
        return
    workplace = workplaces[0]
    fields = []
    if config.qr_static_token_hash and not workplace.qr_token_hash:
        workplace.qr_token_hash = config.qr_static_token_hash
        fields.append('qr_token_hash')
    if config.public_wifi_ip and not workplace.public_wifi_ip:
        workplace.public_wifi_ip = config.public_wifi_ip
        fields.append('public_wifi_ip')
    if fields:
        workplace.save(update_fields=fields)


class Migration(migrations.Migration):
    dependencies = [
        ('companies', '0002_seed_initial_company'),
        ('core', '0003_businessconfig_maintenance_enabled_and_more'),
    ]

    operations = [migrations.RunPython(copy_legacy_clock_credentials, migrations.RunPython.noop)]
