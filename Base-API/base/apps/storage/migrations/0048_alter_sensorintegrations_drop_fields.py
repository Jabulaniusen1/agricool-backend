# Generated manually on 2025-04-16 11:00

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0047_replace_sensor_fields_with_source_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sensorintegration",
            name="account_key",
        ),
        migrations.RemoveField(
            model_name="sensorintegration",
            name="machine_id",
        ),
        migrations.RemoveField(
            model_name="sensorintegration",
            name="channel_id",
        ),
        migrations.RemoveField(
            model_name="sensorintegration",
            name="field",
        ),
    ]
