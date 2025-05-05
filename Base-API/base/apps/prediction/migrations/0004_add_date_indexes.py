
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("prediction", "0003_auto_20230826_2309"),
    ]

    operations = [
        # CREATE INDEX prediction_mlmarketdataindia_date_desc ON prediction_mlmarketdataindia (date DESC);
        migrations.AddIndex(
            model_name='mlmarketdataindia',
            index=models.Index(fields=['-date'], name='prediction_mlmarketdataindia_date_desc'),
        ),
        # CREATE INDEX prediction_mlmarketdatanigeria_date_desc ON prediction_mlmarketdatanigeria (date DESC);
        migrations.AddIndex(
            model_name='mlmarketdatanigeria',
            index=models.Index(fields=['-date'], name='prediction_mlmarketdatanigeria_date_desc'),
        ),
    ]
