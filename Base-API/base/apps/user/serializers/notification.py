from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.marketplace.models import MarketListedCratePrice
from base.apps.operation.models import Checkin, Checkout
from base.apps.storage.models import CoolingUnit, Produce
from base.apps.user.models import Farmer, Notification


class NotificationSerializer(serializers.ModelSerializer):
    cooling_unit_name = serializers.SerializerMethodField()
    crates = serializers.SerializerMethodField()
    movement_code = serializers.SerializerMethodField()
    market_listing = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = "__all__"

    def get_market_listing(self, instance):
        try:
            if (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                market_listing_price = MarketListedCratePrice.objects.get(
                    id=instance.specific_id
                )

                return {
                    "price_per_kg": market_listing_price.produce_price_per_kg,
                    "currency": market_listing_price.market_listed_crate.currency,
                }

            return None
        except:
            return None

    def get_cooling_unit_name(self, instance):
        try:
            cu = None

            if instance.event_type == "SENSOR_ERROR":
                cu = CoolingUnit.objects.get(id=instance.specific_id).name

            if (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                cu = (
                    CoolingUnit.objects.filter(
                        crate_cooling_unit__market_listed_crates__prices__id=instance.specific_id
                    )
                    .first()
                    .name
                )

            return cu
        except:
            return None

    def get_crates(self, instance):
        try:
            produce = None

            if (
                instance.event_type == Notification.NotificationType.TIME_TO_PICKUP
                or instance.event_type == Notification.NotificationType.FARMER_SURVEY
            ):
                produce = Produce.objects.get(id=instance.specific_id)

            elif instance.event_type == Notification.NotificationType.MARKET_SURVEY:
                produce = Produce.objects.filter(
                    crates__partial_checkouts__checkout_id=instance.specific_id
                ).first()

            elif instance.event_type == Notification.NotificationType.CHECKOUT_EDITED:
                produce = Produce.objects.filter(
                    checkin_id=instance.specific_id
                ).first()

            elif instance.event_type == Notification.NotificationType.ORDER_REQUIRES_MOVEMENT:
                produce = Produce.objects.filter(
                    checkin__movement_id=instance.specific_id
                ).first()

            elif (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                produce = Produce.objects.filter(
                    crates__market_listed_crates__prices__id=instance.specific_id
                ).first()

            if produce:
                owned_by_user = produce.checkin.owned_by_user

                # Attempt to access the Farmer instance; handle if it does not exist
                try:
                    farmer_profile = owned_by_user.farmer
                except Farmer.DoesNotExist:
                    farmer_profile = None

                first_crate = produce.crates.first()
                cooling_unit = first_crate.cooling_unit

                produce_dict = {
                    "crop": produce.crop.name,
                    "farmer": f"{owned_by_user.first_name} {owned_by_user.last_name}",
                    "farmer_id": farmer_profile.id if farmer_profile else None,
                    "user_id": owned_by_user.id,
                    "checkin_date": produce.checkin.movement.date,
                    "cooling_unit": cooling_unit.name,
                    "cooling_unit_id": cooling_unit.id,
                }

                return produce_dict
        except:
            pass

        return None

    def get_movement_code(self, instance):
        try:
            if instance.event_type == Notification.NotificationType.MARKET_SURVEY:
                movement_code = Checkout.objects.get(
                    id=instance.specific_id
                ).movement.code
                return movement_code
            elif (
                instance.event_type == Notification.NotificationType.TIME_TO_PICKUP
                or instance.event_type == Notification.NotificationType.FARMER_SURVEY
            ):
                movement_code = Produce.objects.get(
                    id=instance.specific_id
                ).checkin.movement.code
                return movement_code
            elif instance.event_type == Notification.NotificationType.CHECKIN_EDITED:
                movement_code = Checkin.objects.get(
                    id=instance.specific_id
                ).movement.code
                return movement_code
            elif (
                instance.event_type
                == Notification.NotificationType.LISTING_PRICE_UPDATED
            ):
                movement_code = (
                    Checkin.objects.filter(
                        produces__crates__market_listed_crates__prices__id=instance.specific_id
                    )
                    .first()
                    .movement.code
                )
                return movement_code
        except:
            pass

        return None
