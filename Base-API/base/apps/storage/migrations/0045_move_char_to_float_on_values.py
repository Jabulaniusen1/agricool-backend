from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0044_latitude_and_longitude_to_point'),
    ]

    operations = [
        ##
        # Optimize the saved sensory data values
        ##
        migrations.AlterField(
            model_name='coolingunitspecifications',
            name='value',
            field=models.FloatField(null=False),
        ),
        migrations.AlterField(
            model_name='coolingunitspecifications',
            name='set_point_value',
            field=models.FloatField(null=True),
        ),
    ]
