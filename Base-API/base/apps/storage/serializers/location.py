from datetime import datetime

from rest_framework import serializers

from base.apps.user.models import ServiceProvider
from base.apps.user.serializers.company import CompanySerializer

from ..models import CoolingUnit, Location
from .cooling_unit import CoolingUnitSerializer


class LocationSerializer(serializers.ModelSerializer):
    cooling_units = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = "__all__"
        depth = 1

    def validate(self, attrs):
        company = (
            ServiceProvider.objects.get(user_id=self.context["request"].user.id)
        ).company
        attrs["company"] = company
        return attrs

    def create(self, validated_data):
        return Location.objects.create(
            **validated_data,
            date_creation=datetime.now(),
            date_last_modified=datetime.now()
        )

    def update(self, instance, validated_data):
        instance.date_last_modified = datetime.now()
        instance.save()
        return super().update(instance, validated_data)

    def get_cooling_units(self, instance):
        items = CoolingUnit.objects.filter(location=instance, deleted=False)
        serializer = CoolingUnitSerializer(instance=items, many=True, read_only=True)
        return serializer.data

    def get_company(self, instance):
        serializer = CompanySerializer(instance=instance.company, read_only=True)
        return serializer.data
