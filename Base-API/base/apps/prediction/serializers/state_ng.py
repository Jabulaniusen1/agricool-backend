from rest_framework import serializers

from base.apps.prediction.models import StateNg


class StateNgSerializer(serializers.ModelSerializer):

    class Meta:
        model = StateNg
        fields = "__all__"
