from rest_framework import serializers


class SensorIntegrationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(allow_blank=True, allow_null=True)
