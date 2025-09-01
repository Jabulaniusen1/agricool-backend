from django.db import transaction
from rest_framework import serializers

from base.apps.operation.models import Checkout
from base.apps.operation.services.checkout import (
    crates_locked_within_marketplace_pending_orders,
    create_partial_checkout,
)
from base.apps.storage.models import CoolingUnit, Crate, Produce
from base.apps.user.models import Notification


class CheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checkout
        fields = (
            "id",
            "movement",
            "paid",
            "payment_through",
            "payment_gateway",
            "payment_method",
            "currency",
            "discount_amount",
            # Computed fields
            "cmp_last_updated_at",
            "cmp_total_cooling_fees_amount",
            "cmp_total_amount",
        )

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"].data

        cooling_units_to_be_computed = []

        # TODO: can be optimized to a single query
        for c in request["crates"]:
            crate = Crate.objects.get(id=c)

            if crate.cooling_unit_id not in cooling_units_to_be_computed:
                cooling_units_to_be_computed.append(crate.cooling_unit_id)

        check_out_instance = Checkout.objects.create(
            **validated_data,
            # price=price,
            # final_price=price - validated_data.get("price_discount")
        )

        crates = Crate.objects.filter(id__in=request["crates"])

        # Check if the operator can checkout all the crates
        if crates_locked_within_marketplace_pending_orders(
            [crate.id for crate in crates]
        ):
            raise serializers.ValidationError("Operator cannot checkout all the crates")

        for crate in crates:
            create_partial_checkout(
                crate,
                weight_in_kg=crate.weight,
                checkout=check_out_instance,
                compute_dependencies=False,
            )

            crate.compute(save=True)

            notification_instance = Notification.objects.filter(specific_id=crate.id)
            if notification_instance:
                Notification.objects.get(specific_id=crate.id).delete()

        # compute each one of the affected produces
        for produce in Produce.objects.filter(crates__id__in=request["crates"]):
            produce.compute(save=True)

        # calculates cooling unit occupancy in percentage
        for cooling_unit in CoolingUnit.objects.filter(
            id__in=cooling_units_to_be_computed
        ).iterator():
            cooling_unit.compute(save=True)

        # compute check out
        check_out_instance.compute(save=True)

        return check_out_instance
