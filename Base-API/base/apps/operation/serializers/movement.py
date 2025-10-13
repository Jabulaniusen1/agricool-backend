import datetime

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count, Exists, F, OuterRef, Prefetch
from django.db.models.query import QuerySet
from rest_framework import serializers

from base.apps.operation.models import (
    Checkin,
    Checkout,
    MarketsurveyPreprocessing,
    Movement,
)
from base.apps.storage.models import Crate

# Constants
MINIMUM_STORAGE_DAYS = 1


def zero_time_fields(dt):
    """Utility function to zero out time fields from datetime."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


class MovementCrateSerializer(serializers.ModelSerializer):
    crop_id = serializers.PrimaryKeyRelatedField(
        source="produce.crop_id", read_only=True
    )
    amount = serializers.FloatField(
        source="price_per_crate_per_pricing_type", read_only=True
    )
    fully_checked_out = serializers.BooleanField(source="cmp_fully_checked_out")
    days_in_storage = serializers.SerializerMethodField()
    calculated_total_price = serializers.FloatField(
        source="price_per_crate_per_pricing_type", read_only=True
    )

    class Meta:
        model = Crate
        fields = [
            "id",
            "crop_id",
            "remaining_shelf_life",
            "planned_days",
            "weight",
            "initial_weight",
            "amount",
            "tag",
            "fully_checked_out",
            "days_in_storage",
            "calculated_total_price",
        ]

    def get_days_in_storage(self, crate):
        checkin_date = zero_time_fields(
            crate.produce.checkin.movement.date.replace(tzinfo=None)
        )

        if crate.cmp_fully_checked_out:
            # get checkout date
            checkout_date = zero_time_fields(
                crate.partial_checkouts.last()
                .checkout.movement.date.replace(tzinfo=None)
            )

            duration = (checkout_date - checkin_date).days
            current_storage_days = MINIMUM_STORAGE_DAYS if duration == 0 else duration

            return current_storage_days

        midnight = zero_time_fields(datetime.datetime.now())

        duration = (midnight - checkin_date).days
        current_storage_days = MINIMUM_STORAGE_DAYS if duration == 0 else duration

        return current_storage_days


class MovementCrateCheckoutSerializer(MovementCrateSerializer):
    owned_by_user_id = serializers.PrimaryKeyRelatedField(
        source="produce.checkin.owned_by_user_id", read_only=True
    )
    owned_on_behalf_of_company_id = serializers.PrimaryKeyRelatedField(
        source="produce.checkin.owned_on_behalf_of_company_id", read_only=True
    )
    affected_weight = serializers.SerializerMethodField()

    # override Meta.fields to include fields from MovementCrateSerializer
    class Meta(MovementCrateSerializer.Meta):
        fields = MovementCrateSerializer.Meta.fields + [
            "owned_by_user_id",
            "owned_on_behalf_of_company_id",
            "affected_weight",
        ]

    def __init__(self, *args, **kwargs):
        self.partial_checkouts = kwargs.pop("partial_checkouts", None)
        super().__init__(*args, **kwargs)

    def get_affected_weight(self, crate):
        affected_partial_checkout = (
            self.partial_checkouts.filter(crate=crate).first()
            if self.partial_checkouts
            else None
        )

        if affected_partial_checkout:
            return affected_partial_checkout.weight_in_kg

        return 0


class MovementCheckinSerializer(serializers.ModelSerializer):
    crates = serializers.SerializerMethodField()

    class Meta:
        model = Checkin
        fields = [
            "id",
            "owned_by_user_id",
            "owned_on_behalf_of_company_id",
            "crates",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance:
            return

        self.crates = [
            crate
            for produce in self.instance.produces.all()
            for crate in produce.crates.all()
        ]

    def get_crates(self, checkin):
        return MovementCrateSerializer(self.crates, many=True).data


class MovementCheckoutSerializer(serializers.ModelSerializer):
    crates = serializers.SerializerMethodField()
    has_market_survey = serializers.SerializerMethodField()
    market_survey_delay = serializers.SerializerMethodField()
    calculated_price = serializers.FloatField(source="cmp_total_cooling_fees_amount")
    discount = serializers.FloatField(source="discount_amount")
    total_price = serializers.FloatField(source="cmp_total_amount")

    class Meta:
        model = Checkout
        fields = [
            "id",
            "payment_gateway",
            "payment_method",
            "payment_through",
            "crates",
            "has_market_survey",
            "market_survey_delay",
            "calculated_price",
            "discount",
            "total_price",
        ]

    def get_crates(self, checkout):
        partial_checkouts = checkout.partial_checkouts.all()

        crates = (
            [partial_checkout.crate for partial_checkout in partial_checkouts]
            if hasattr(self.instance, "partial_checkouts")
            else []
        )

        return MovementCrateCheckoutSerializer(
            crates, many=True, partial_checkouts=partial_checkouts
        ).data

    def get_has_market_survey(self, checkout):
        return getattr(checkout, "crop_ids_with_market_surveys", None) or []

    def get_market_survey_delay(self, checkout):
        """
        Determines if there is a delay in the market survey process for a given movement.
        """

        has_been_preprocessed = getattr(checkout, "has_been_preprocessed", 0)

        if not has_been_preprocessed:
            return False

        crops_to_be_filled_count = getattr(checkout, "crops_to_be_filled_count", 0)
        attached_surveys_distinct_produce_crop_count = getattr(
            checkout, "attached_surveys_distinct_produce_crop_count", 0
        )
        has_survey_to_be_filled = (
            attached_surveys_distinct_produce_crop_count < crops_to_be_filled_count
        )

        if (
            attached_surveys_distinct_produce_crop_count > 0
            and not has_survey_to_be_filled
        ):
            return False

        return True


class MovementOrderSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(source="order", read_only=True)

    class Meta:
        fields = "id"


class MovementSerializer(serializers.ModelSerializer):
    checkin = MovementCheckinSerializer(required=False)
    checkout = MovementCheckoutSerializer(required=False)
    order = MovementOrderSerializer(required=False)
    operator = serializers.SerializerMethodField()
    cooling_unit_id = serializers.SerializerMethodField()

    class Meta:
        model = Movement
        fields = (
            "id",
            "code",
            "date",
            "initiated_for",
            "cooling_unit_id",
            "checkin",
            "checkout",
            "order",
            "operator",
        )

    @staticmethod
    def optimized_init(queryset):
        crates_subquery = (
            Crate.objects.all()
            .select_related(
                "cooling_unit",
                "produce",
                "produce__crop",
                "produce__checkin",
                "produce__checkin__movement",
                "produce__checkin__owned_by_user",
            )
            .distinct()
        )

        return MovementSerializer(
            (
                queryset.select_related(
                    "operator",
                    "operator__user",
                ).prefetch_related(
                    Prefetch(
                        "checkins",
                        (
                            Checkin.objects.prefetch_related(
                                "owned_by_user",
                                Prefetch("produces__crates", queryset=crates_subquery),
                            )
                        ),
                    ),
                    Prefetch(
                        "checkouts",
                        queryset=(
                            Checkout.objects
                            # .filter(partial_checkouts__isnull=False)
                            .prefetch_related(
                                Prefetch(
                                    "partial_checkouts__crate", queryset=crates_subquery
                                ),
                            ).annotate(
                                has_been_preprocessed=Exists(
                                    MarketsurveyPreprocessing.objects.filter(
                                        checkout_id=OuterRef("id"),
                                        is_active=True,
                                    )
                                ),
                                crop_ids_with_market_surveys=ArrayAgg(
                                    F("survey_checkout__crop"), distinct=True
                                ),
                                attached_surveys_distinct_produce_crop_count=Count(
                                    F("survey_checkout__crop"), distinct=True
                                ),
                                crops_to_be_filled_count=Count(
                                    "partial_checkouts__crate__produce__crop",
                                    distinct=True,
                                ),
                            )
                        ),
                    ),
                )
            ),
            many=True,
        )

    def __init__(self, *args, **kwargs):
        # Don't accept instance that is not a queryset
        if not isinstance(args[0], QuerySet):
            raise TypeError("instance must be a queryset")

        super().__init__(*args, **kwargs)

    def to_representation(self, movement):
        representation = super().to_representation(movement)

        checkin = movement.checkins.first()
        checkout = movement.checkouts.first()
        order = movement.order

        representation["checkin"] = (
            MovementCheckinSerializer(checkin).data if checkin else None
        )
        representation["checkout"] = (
            MovementCheckoutSerializer(checkout).data if checkout else None
        )
        representation["order"] = MovementOrderSerializer(order).data if order else None

        return representation

    def get_cooling_unit_id(self, obj):
        try:
            checkout = obj.checkouts.first()
            if checkout:
                return checkout.partial_checkouts.first().crate.cooling_unit_id

            checkin = obj.checkins.first()
            if checkin:
                return checkin.produces.first().crates.first().cooling_unit_id

        except AttributeError:
            return None

        return None

    def get_operator(self, movement):
        return (
            movement.operator.user.first_name + " " + movement.operator.user.last_name
            if movement.operator
            else None
        )
