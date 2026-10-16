from django.db import migrations


def normalizar_puestos(apps, schema_editor):
    Turno = apps.get_model('scheduling', 'Shift')
    Turno.objects.filter(position='kitchen').update(position='cocinero')
    Turno.objects.exclude(position__in=['camarero', 'cocinero']).update(position='camarero')


class Migration(migrations.Migration):
    dependencies = [
        ('scheduling', '0002_alter_shift_created_at_alter_shift_date_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_puestos, migrations.RunPython.noop),
    ]
