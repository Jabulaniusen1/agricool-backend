from rest_framework import serializers
from ..models import (
    Crop,
    CoolingUnitCrop,
)

class CoolingUnitCropSerializer(serializers.ModelSerializer):
    full_crop = serializers.SerializerMethodField()

    class Meta:
        model = CoolingUnitCrop
        fields = "__all__"

    def get_full_crop(self, instance):
        return Crop.objects.filter(id=instance.crop.id).values()[0]
