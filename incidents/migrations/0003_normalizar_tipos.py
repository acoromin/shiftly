from django.db import migrations


def normalizar_tipos(apps, schema_editor):
    Incidencia = apps.get_model('incidents', 'Incident')
    tipos_permitidos = ['missing_clock_in', 'missing_clock_out', 'clock_error', 'other']
    Incidencia.objects.exclude(incident_type__in=tipos_permitidos).update(incident_type='other')


class Migration(migrations.Migration):
    dependencies = [
        ('incidents', '0002_alter_incident_created_at_alter_incident_date_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_tipos, migrations.RunPython.noop),
    ]
