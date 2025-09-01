import base64
import os

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.user.models import GenericUserCode


class GenericCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenericUserCode
        fields = "__all__"

    def create(self, validated_data):
        code = base64.urlsafe_b64encode(os.urandom(6)).decode()
