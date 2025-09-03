# Generated manually for renaming runDT to run_dt field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0049_deduplicate_cooling_unit_specs'),
    ]

    operations = [
        migrations.RenameField(
            model_name='crate',
            old_name='runDT',
            new_name='run_dt',
        ),
    ]