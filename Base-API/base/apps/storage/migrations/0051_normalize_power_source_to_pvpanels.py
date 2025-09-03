from django.db import migrations


def normalize_power_source_to_pvpanels(apps, schema_editor):
    """
    Normalize all power_source values to 'pvpanels' to maintain consistency
    in the CoolingUnitPower model.
    """
    CoolingUnitPower = apps.get_model('storage', 'CoolingUnitPower')
    
    # Update all variants of PV panels to use consistent 'pvpanels' value
    variants_to_normalize = ['PVPANELS', 'PV_PANELS', 'pv_panels', 'pvpanels']
    
    for variant in variants_to_normalize:
        CoolingUnitPower.objects.filter(power_source=variant).update(power_source='pvpanels')

class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0050_rename_rundt_to_run_dt'),
    ]

    operations = [
        migrations.RunPython(
            normalize_power_source_to_pvpanels,
        ),
    ]