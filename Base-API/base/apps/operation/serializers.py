import datetime
import json

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Prefetch
from django.db.models.query import QuerySet
from rest_framework import serializers

from base.celery import app
from base.apps.operation.services.checkout import (
    crates_locked_within_marketplace_pending_orders, create_partial_checkout)
from base.apps.prediction.models import Market
from base.apps.storage.models import (CoolingUnit, CoolingUnitCrop, Crate, Crop,
                                      Produce)
from base.apps.storage.services.ttpu import compute_initial_ttpu_checkin
from base.apps.user.models import (FarmerSurvey, FarmerSurveyCommodity,
                                   Notification, Operator)

from .models import Checkin, Checkout, MarketSurvey, Movement


class MovementCrateSerializer(serializers.ModelSerializer):
    crop_id = serializers.PrimaryKeyRelatedField(source='produce.crop_id', read_only=True)
    amount = serializers.FloatField(source='price_per_crate_per_pricing_type', read_only=True)
    fully_checked_out = serializers.BooleanField(source='cmp_fully_checked_out')
    days_in_storage = serializers.SerializerMethodField()

    class Meta:
        model = Crate
        fields = [
            'id',
            'crop_id',
            'remaining_shelf_life',
            'planned_days',
            'weight',
            'initial_weight',
            'amount',
            'tag',
            'fully_checked_out',
            'days_in_storage',
        ]

    def get_days_in_storage(self, crate):
        checkin_date = crate.produce.checkin.movement.date.replace(
            tzinfo=None
        ).replace(hour=0, minute=0, second=0, microsecond=0)

        if crate.cmp_fully_checked_out:
            # get checkout date
            checkout_date = crate.partial_checkouts.last().checkout.movement.date.replace(
                tzinfo=None
            ).replace(hour=0, minute=0, second=0, microsecond=0)

            duration = (checkout_date - checkin_date).days
            current_storage_days = 1 if duration == 0 else duration

            return current_storage_days

        midnight = datetime.datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        duration = (midnight - checkin_date).days
        current_storage_days = 1 if duration == 0 else duration

        return current_storage_days

class MovementCrateCheckoutSerializer(MovementCrateSerializer):
    owned_by_user_id = serializers.PrimaryKeyRelatedField(source='produce.checkin.owned_by_user_id', read_only=True)
    owned_on_behalf_of_company_id = serializers.PrimaryKeyRelatedField(source='produce.checkin.owned_on_behalf_of_company_id', read_only=True)
    affected_weight = serializers.SerializerMethodField()

    # override Meta.fields to include fields from MovementCrateSerializer
    class Meta(MovementCrateSerializer.Meta):
        fields = MovementCrateSerializer.Meta.fields + [
            'owned_by_user_id',
            'owned_on_behalf_of_company_id',
            'affected_weight',
        ]

    def __init__(self, *args, **kwargs):
        self.partial_checkouts = kwargs.pop("partial_checkouts", None)
        super().__init__(*args, **kwargs)



    def get_affected_weight(self, crate):
        affected_partial_checkout = self.partial_checkouts.filter(crate=crate).first() if self.partial_checkouts else None

        if affected_partial_checkout:
            return affected_partial_checkout.weight_in_kg

        return 0

class MovementCheckinSerializer(serializers.ModelSerializer):
    crates = serializers.SerializerMethodField()

    class Meta:
        model = Checkin
        fields = [
            'id',
            'owned_by_user_id',
            'owned_on_behalf_of_company_id',
            'crates',
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
    calculated_price = serializers.FloatField(source='cmp_total_cooling_fees_amount')
    discount = serializers.FloatField(source='discount_amount')
    total_price = serializers.FloatField(source='cmp_total_amount')

    class Meta:
        model = Checkout
        fields = [
            'id',
            'payment_gateway',
            'payment_method',
            'payment_through',
            'crates',
            'has_market_survey',
            'market_survey_delay',
            'calculated_price',
            'discount',
            'total_price',
        ]

    def get_crates(self, checkout):
        partial_checkouts = checkout.partial_checkouts.all()

        crates = [
            partial_checkout.crate
            for partial_checkout in partial_checkouts
        ] if hasattr(self.instance, "partial_checkouts") else []

        return MovementCrateCheckoutSerializer(crates, many=True, partial_checkouts=partial_checkouts).data

    def get_has_market_survey(self, checkout):
        return getattr(checkout, 'crop_ids_with_market_surveys', None) or []

    def get_market_survey_delay(self, checkout):
        """
        Determines if there is a delay in the market survey process for a given movement.
        """

        has_been_preprocessed = getattr(checkout, "has_been_preprocessed", 0)

        if not has_been_preprocessed:
            return False

        crops_to_be_filled_count = getattr(checkout, "crops_to_be_filled_count", 0)
        attached_surveys_distinct_produce_crop_count = getattr(checkout, "attached_surveys_distinct_produce_crop_count", 0)
        has_survey_to_be_filled = attached_surveys_distinct_produce_crop_count < crops_to_be_filled_count

        if (
            attached_surveys_distinct_produce_crop_count > 0 and
            not has_survey_to_be_filled
        ):
            return False

        return True


class MovementOrderSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(source='order', read_only=True)

    class Meta:
        fields = ('id')


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
                'cooling_unit',
                'produce',
                'produce__crop',
                'produce__checkin',
                'produce__checkin__movement',
                'produce__checkin__owned_by_user',
            )
            .distinct()
        )

        return MovementSerializer((
            queryset
            .select_related(
                "operator",
                "operator__user",
            )
            .prefetch_related(
                Prefetch("checkins", (
                    Checkin.objects
                    .prefetch_related(
                        "owned_by_user",
                        Prefetch("produces__crates", queryset=crates_subquery),
                    )
                )),
                Prefetch("checkouts", queryset=(
                    Checkout.objects
                    # .filter(partial_checkouts__isnull=False)
                    .prefetch_related(
                        Prefetch("partial_checkouts__crate", queryset=crates_subquery),
                    )
                    .annotate(
                        has_been_preprocessed=Exists(
                            MarketsurveyPreprocessing.objects.filter(
                                checkout_id=OuterRef("id"),
                                is_active=True,
                            )
                        ),
                        crop_ids_with_market_surveys=ArrayAgg(
                            F("survey_checkout__crop"),
                            distinct=True
                        ),
                        attached_surveys_distinct_produce_crop_count=Count(
                            F('survey_checkout__crop'),
                            distinct=True
                        ),
                        crops_to_be_filled_count=Count("partial_checkouts__crate__produce__crop", distinct=True),
                    )
                )),
            )
        ), many=True)


    def __init__(self, *args, **kwargs):
        # Don't accept instance that is not a queryset
        if not isinstance(args[0], QuerySet):
            raise Exception("instance must be a queryset")

        super().__init__(*args, **kwargs)

    def to_representation(self, movement):
        representation = super().to_representation(movement)

        checkin = movement.checkins.first()
        checkout = movement.checkouts.first()
        order = movement.order

        representation['checkin'] = MovementCheckinSerializer(checkin).data if checkin else None
        representation['checkout'] = MovementCheckoutSerializer(checkout).data if checkout else None
        representation['order'] = MovementOrderSerializer(order).data if order else None

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


class CheckinSerializer(serializers.ModelSerializer):
    has_dt = serializers.SerializerMethodField()
    produces = serializers.SerializerMethodField()

    class Meta:
        model = Checkin
        fields = ("id", "movement", "owned_by_user", "owned_on_behalf_of_company", "has_dt", "produces")

    @transaction.atomic
    def create(self, validated_data):
        operator = Operator.objects.get(user=self.context["request"].user)
        company = operator.company
        request = self.context["request"].data

        checkin_instance = Checkin.objects.create(**validated_data)

        farmerSurvey = FarmerSurvey.objects.filter(farmer__user=checkin_instance.owned_by_user).first()

        # deserialize the produces field
        produces = json.loads(request["produces"])

        # creating and array to runDT
        produces_for_DT = []

        # getting all the pictures
        pictures = dict(request).get("pictures[]")
        # getting the produces and the index to map with the picture
        for produce in produces:
            crop = Crop.objects.get(id=produce["crop"]["id"])
            # Checking if the produce has picture to retrieve the first picture of the list
            if produce["hasPicture"]:
                # Removing the first picture of the list and storing it in the produce['picture']
                produce["picture"] = pictures.pop(0)
            # Removing the field hasPicture from the produce
            produce.pop("hasPicture")
            produce.pop("crop")
            crates = produce.pop("crates")
            produce_instance = Produce.objects.create(
                **produce, crop=crop, checkin=checkin_instance
            )

            for crate in crates:
                price = 0
                # as we are in check in, better to take the cooling unit from the request and use it!
                cooling_unit = CoolingUnit.objects.get(id=crate["cooling_unit_id"])

                # calculates pricing based on cooling unit pricing and crop type price
                cup_crop = CoolingUnitCrop.objects.get(
                    cooling_unit_id=crate["cooling_unit_id"], crop=crop
                )
                metric_multiplier = (
                    crate["weight"] if cooling_unit.metric == "KILOGRAMS" else 1
                )

                if cup_crop.pricing.pricing_type == "FIXED":
                    price += metric_multiplier * cup_crop.pricing.fixed_rate
                elif cup_crop.pricing.pricing_type == "PERIODICITY":
                    price += metric_multiplier * cup_crop.pricing.daily_rate

                # Parse weight as an integer
                crate["weight"] = int(crate["weight"])

                if crate["weight"] <= 0:
                    raise serializers.ValidationError("Weight must be greater than 0")

                crate = Crate.objects.create(
                    **crate,
                    initial_weight=crate["weight"],
                    cooling_unit=cooling_unit,
                    produce=produce_instance,
                    remaining_shelf_life=None,
                    price_per_crate_per_pricing_type=price,
                    currency=company.currency
                )

            # THERESA check if oos still works here or we need to define
            if (crop.digital_twin_identifier) and (cooling_unit.location.company.digital_twin is True):
                produces_for_DT.append(produce_instance)

            # TODO - run the checks for each produce's crop here - and send the notification to the farmer + operator if needed
            sendNotification = False

            if not farmerSurvey:
                sendNotification = True
            else:
                if not FarmerSurveyCommodity.objects.filter(
                    farmer_survey=farmerSurvey.id, crop=crop
                ).exists():
                    sendNotification = True

            if sendNotification:
                # send notifications to operator and farmer
                Notification.objects.create(
                    user=checkin_instance.owned_by_user,
                    specific_id=produce_instance.id,
                    event_type="FARMER_SURVEY",
                )

                Notification.objects.create(
                    user=operator.user,
                    specific_id=produce_instance.id,
                    event_type="FARMER_SURVEY",
                )
            else:
                print("farmer survey commodity exists", farmerSurvey.id, crop)

        # Handle DTs and TTPU for produces
        if len(produces_for_DT) > 0:
            # Update the crates to activate runDT as a single update call.
            Crate.objects.filter(produce__in=produces_for_DT).update(runDT=True)

            # Compute the initial TTPU for each produce added in this checkin.
            for produce in produces_for_DT:
                compute_initial_ttpu_checkin(produce.id, produce.crates.first().id)

        return checkin_instance
    def get_has_dt(self, instance):
        produce = Produce.objects.filter(checkin=instance)
        return produce[0].crop.digital_twin_identifier

    def get_produces(self, instance):
        return Produce.objects.filter(checkin=instance).annotate(
            crates_ids=ArrayAgg('crates__id')
        ).values('id', 'crop_id', 'crates_ids')

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
        if crates_locked_within_marketplace_pending_orders([crate.id for crate in crates]):
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
        for cooling_unit in CoolingUnit.objects.filter(id__in=cooling_units_to_be_computed).iterator():
            cooling_unit.compute(save=True)

        # compute check out
        check_out_instance.compute(save=True)

        return check_out_instance


from base.apps.operation.models import (MarketsurveyCheckout,
                                        MarketsurveyPreprocessing)


class MarketSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketSurvey
        fields = "__all__"

    def validate(self, data):

        request = self.context["request"]

        market_survey_filled = MarketSurvey.objects.filter(
            crop=request.data["crop"],
            marketsurveycheckout_market_survey__checkout=request.data["checkout"],
        ).exists()

        if market_survey_filled:
            raise serializers.ValidationError(
                "Market survey already filled for this checkout and crop"
            )

        has_been_preprocessed = MarketsurveyPreprocessing.objects.filter(
            checkout=request.data["checkout"],
            crop=request.data["crop"],
        ).exists()

        if not has_been_preprocessed:
            raise serializers.ValidationError(
                "Market survey unavailable for this checkout"
            )

        # TODO: if in Nigeria, get state data instead of market
        if "local_market" in request.data and request.data["local_market"] is not None:
            local_market = request.data.pop("local_market")
            target_market = Market.objects.filter(
                name=local_market["market"], state__name=local_market["state"]
            )
            if not target_market.exists():
                raise serializers.ValidationError(
                    "Market not found, please register it"
                )
            data["market"] = target_market.first()

        return data

    def create(self, validated_data):

        market_survey = MarketSurvey.objects.create(
            **validated_data, date_filled_in=datetime.datetime.now().astimezone()
        )

        self.attach_to_similar_crops(market_survey, validated_data["checkout"])

        return market_survey

    def attach_to_similar_crops(self, markey_survey, checkout):

        current = MarketsurveyPreprocessing.objects.filter(
            checkout=checkout, crop=markey_survey.crop
        ).first()

        valid_checkouts = MarketsurveyPreprocessing.objects.filter(
            crop=current.crop,
            farmer=current.farmer,
            operator=current.operator,
            is_active=True,
        ).distinct("checkout")

        for i in valid_checkouts:
            MarketsurveyCheckout.objects.create(
                checkout=i.checkout, marketsurvey=markey_survey
            )
