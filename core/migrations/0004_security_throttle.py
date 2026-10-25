from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0003_businessconfig_maintenance_enabled_and_more')]

    operations = [
        migrations.CreateModel(
            name='SecurityThrottle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=64, unique=True)),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('window_started_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'indexes': [models.Index(fields=['updated_at'], name='core_secur_updated_a6d58d_idx')]},
        ),
    ]
