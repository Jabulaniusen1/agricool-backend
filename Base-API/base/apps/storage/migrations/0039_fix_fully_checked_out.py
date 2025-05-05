from django.db import migrations, models

def set_fully_checked_out_when_weight_is_zero(apps, schema_editor):
    Crate = apps.get_model('storage', 'Crate')
    Crate.objects.filter(weight=0).update(fully_checked_out=True)

class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0038_auto_20241105_1449'),
    ]

    operations = [
         migrations.RunPython(set_fully_checked_out_when_weight_is_zero, reverse_code=migrations.RunPython.noop),
    ]
