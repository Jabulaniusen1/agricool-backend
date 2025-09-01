import json

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from rest_framework import serializers

from base.apps.operation.models import Checkin
from base.apps.storage.models import Produce
from base.apps.user.models import Operator


class CheckinSerializer(serializers.ModelSerializer):
    has_dt = serializers.SerializerMethodField()
    produces = serializers.SerializerMethodField()

    class Meta:
        model = Checkin
        fields = (
            "id",
            "movement",
            "owned_by_user",
            "owned_on_behalf_of_company",
            "has_dt",
            "produces",
        )

    @transaction.atomic
    def create(self, validated_data):
        checkin_instance = Checkin.objects.create(**validated_data)
        produces_payload = json.loads(self.context["request"].data["produces"])

        operator = Operator.objects.get(user=self.context["request"].user)
        from base.apps.operation.services.checkin import handle_produces_for_checkin

        handle_produces_for_checkin(checkin_instance, produces_payload, operator)

        return checkin_instance

    def get_has_dt(self, instance):
        produce = Produce.objects.filter(checkin=instance)
        return produce[0].crop.digital_twin_identifier

    def get_produces(self, instance):
        return (
            Produce.objects.filter(checkin=instance)
            .annotate(crates_ids=ArrayAgg("crates__id"))
            .values("id", "crop_id", "crates_ids")
        )
