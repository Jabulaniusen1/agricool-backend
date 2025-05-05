from rest_framework import serializers

from ..models import Pricing


class PricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = "__all__"

    def create(self, validated_data):
        return Pricing.objects.create(**validated_data)
