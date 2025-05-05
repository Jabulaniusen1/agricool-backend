from rest_framework import serializers

from ..models import CoolingUnitSpecifications


class CoolingUnitSpecificationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoolingUnitSpecifications
        fields = "__all__"
