from django.db import migrations


def normalizar_roles_y_puestos(apps, schema_editor):
    PerfilEmpleado = apps.get_model('employees', 'EmployeeProfile')
    PerfilEmpleado.objects.filter(role='admin').update(role='administrador')
    PerfilEmpleado.objects.filter(role='manager').update(role='trabajador')
    PerfilEmpleado.objects.filter(role='worker').update(role='trabajador')
    PerfilEmpleado.objects.filter(primary_position='kitchen').update(primary_position='cocinero')
    PerfilEmpleado.objects.exclude(primary_position__in=['camarero', 'cocinero']).update(
        primary_position='camarero'
    )


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0002_alter_employeeprofile_options_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_roles_y_puestos, migrations.RunPython.noop),
    ]
