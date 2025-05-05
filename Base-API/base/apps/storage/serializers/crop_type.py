from rest_framework import serializers

from ..models import CropType


class CropTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = (
            "id",
            "name",
        )
