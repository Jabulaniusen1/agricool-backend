from rest_framework import serializers

from ..models import Crop


class CropSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Crop
        fields = "__all__"

    def get_image(self, instance):
        return instance.image.name
