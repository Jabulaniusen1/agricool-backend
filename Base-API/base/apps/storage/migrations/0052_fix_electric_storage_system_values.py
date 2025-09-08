# Generated data migration to fix ElectricStorageSystem choice values

from django.db import migrations


def fix_electric_storage_system_values(apps, schema_editor):
    """
    Fix ElectricStorageSystem values that may have been stored as display labels
    instead of the actual database values.
    """
    CoolingUnitPower = apps.get_model('storage', 'CoolingUnitPower')
    
    value_mapping = {
        'BATTERY': 'battery',
        'ice-pack': 'thermal storage',
        'HYBRID': 'hybrid',
        'NONE': 'none',
    }
    
    for old_value, new_value in value_mapping.items():
        CoolingUnitPower.objects.filter(
            electricity_storage_system=old_value
        ).update(electricity_storage_system=new_value)


def reverse_fix_electric_storage_system_values(apps, schema_editor):
    """
    Reverse migration - convert back to display labels (not recommended)
    """
    CoolingUnitPower = apps.get_model('storage', 'CoolingUnitPower')
    
    reverse_mapping = {
        'battery': 'BATTERY',
        'thermal storage': 'ice-pack',
        'hybrid': 'HYBRID',  
        'none': 'NONE',
    }
    
    for old_value, new_value in reverse_mapping.items():
        CoolingUnitPower.objects.filter(
            electricity_storage_system=old_value
        ).update(electricity_storage_system=new_value)


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0051_normalize_power_source_to_pvpanels'),
    ]

    operations = [
        migrations.RunPython(
            fix_electric_storage_system_values,
            reverse_fix_electric_storage_system_values,
        ),
    ]