# Generated manually for renaming isUnknown to is_unknown field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0031_alter_notification_event_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='farmer',
            old_name='isUnknown',
            new_name='is_unknown',
        ),
    ]