from django.db import migrations


def normalizar_tipos(apps, schema_editor):
    Solicitud = apps.get_model('leaves', 'LeaveRequest')
    tipos_permitidos = ['vacation', 'day_off', 'justified_absence', 'medical_absence']
    Solicitud.objects.exclude(request_type__in=tipos_permitidos).update(
        request_type='justified_absence'
    )


class Migration(migrations.Migration):
    dependencies = [
        ('leaves', '0002_alter_leaverequest_options_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_tipos, migrations.RunPython.noop),
    ]
