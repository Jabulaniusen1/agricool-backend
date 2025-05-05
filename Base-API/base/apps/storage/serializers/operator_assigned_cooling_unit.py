from rest_framework import serializers

from ..models import OperatorAssignedCoolingUnit


class OperatorAssignedCoolingUnitSerializer(serializers.ModelSerializer):
    operator_id = serializers.SerializerMethodField()

    class Meta:
        model = OperatorAssignedCoolingUnit
        fields = ("id", "operator_id", "date")

    def get_operator_id(self, instance):
        return instance.operator.id
