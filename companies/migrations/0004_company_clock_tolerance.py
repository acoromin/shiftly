from django.db import migrations, models
from django.core.validators import MaxValueValidator


def preserve_existing_tolerance(apps, schema_editor):
    alias = schema_editor.connection.alias
    Company = apps.get_model('companies', 'Company')
    BusinessConfig = apps.get_model('core', 'BusinessConfig')
    config = BusinessConfig.objects.using(alias).filter(pk=1).first()
    if config is not None:
        # Every existing company used this global value before this migration.
        Company.objects.using(alias).update(clock_tolerance_minutes=config.clock_tolerance_minutes)


class Migration(migrations.Migration):
    dependencies = [
        ('companies', '0003_copy_legacy_clock_credentials'),
        ('core', '0003_businessconfig_maintenance_enabled_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='company', name='clock_tolerance_minutes',
            field=models.PositiveSmallIntegerField(
                default=5, verbose_name='minutos de tolerancia', validators=[MaxValueValidator(32767)],
            ),
        ),
        migrations.RunPython(preserve_existing_tolerance, migrations.RunPython.noop),
    ]
