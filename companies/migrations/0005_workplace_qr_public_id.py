import uuid

from django.db import migrations, models


def assign_public_ids(apps, schema_editor):
    Workplace = apps.get_model('companies', 'Workplace')
    alias = schema_editor.connection.alias
    batch = []
    for workplace in Workplace.objects.using(alias).only('pk').iterator(chunk_size=500):
        workplace.qr_public_id = uuid.uuid4()
        batch.append(workplace)
        if len(batch) == 500:
            Workplace.objects.using(alias).bulk_update(batch, ['qr_public_id'], batch_size=500)
            batch.clear()
    if batch:
        Workplace.objects.using(alias).bulk_update(batch, ['qr_public_id'], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [('companies', '0004_company_clock_tolerance')]

    operations = [
        migrations.AddField(
            model_name='workplace', name='qr_public_id',
            field=models.UUIDField(null=True, editable=False, verbose_name='identificador publico del QR'),
        ),
        migrations.RunPython(assign_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='workplace', name='qr_public_id',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False,
                                   verbose_name='identificador publico del QR'),
        ),
    ]
