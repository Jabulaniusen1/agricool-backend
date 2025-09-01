from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.storage.models import CoolingUnit
from base.apps.user.models import Operator
from base.apps.user.serializers.company import CompanySerializer
from base.apps.user.serializers.user import UserSerializer


class OperatorSerializer(serializers.ModelSerializer):
    company = CompanySerializer(many=False)
    user = UserSerializer()
    cooling_units = serializers.SerializerMethodField()

    class Meta:
        model = Operator
        fields = ("id", "user", "company", "cooling_units")

    def get_cooling_units(self, instance):
        cooling_units = CoolingUnit.objects.filter(
            operators=instance.user, deleted=False
        ).values_list("id", flat=True)
        return cooling_units
