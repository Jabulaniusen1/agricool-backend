from rest_framework import serializers

from ..models import CoolingUnitPower


class CoolingUnitPowerSerializer(serializers.ModelSerializer):
    refrigerant_type = serializers.ChoiceField(
        choices=CoolingUnitPower.RefrigerantType.choices
    )
    power_source = serializers.ChoiceField(choices=CoolingUnitPower.PowerSource.choices)
    electricity_storage_system = serializers.ChoiceField(
        choices=CoolingUnitPower.ElectricStorageSystem.choices
    )
    thermal_storage_method = serializers.ChoiceField(
        choices=CoolingUnitPower.ThermalStorageMethod.choices
    )

    class Meta:
        model = CoolingUnitPower
        fields = "__all__"

    def create(self, validated_data):
        cooling_unit_power_instance = CoolingUnitPower.objects.create(**validated_data)

        return cooling_unit_power_instance
