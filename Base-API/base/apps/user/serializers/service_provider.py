from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.user.models import ServiceProvider
from base.apps.user.serializers.company import CompanySerializer
from base.apps.user.serializers.user import UserSerializer

class ServiceProviderSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False)
    user = UserSerializer()

    class Meta:
        model = ServiceProvider
        fields = ("id", "user", "company")
