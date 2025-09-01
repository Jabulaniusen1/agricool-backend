from rest_framework import serializers

from base.apps.storage.services.cooling_unit_capacity import \
    get_weekly_capacity_forecast

from ..models import CoolingUnit


class CoolingUnitCapacitySerializer(serializers.ModelSerializer):
    used_capacity = serializers.SerializerMethodField()

    class Meta:
        model = CoolingUnit
        fields = ("id", "used_capacity")

    def get_used_capacity(self, instance):
        return get_weekly_capacity_forecast(instance)
