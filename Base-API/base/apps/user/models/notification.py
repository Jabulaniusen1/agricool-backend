from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from .user import User


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        SENSOR_ERROR = "SENSOR_ERROR", "Sensor error"
        MARKET_SURVEY = "MARKET_SURVEY", "Market survey"
        TIME_TO_PICKUP = "TIME_TO_PICKUP", "Time to pick up"
        CHECKIN_EDITED = "CHECKIN_EDITED", "Checkin edited"
        ORDER_REQUIRES_MOVEMENT = "ORDER_REQUIRES_MOVEMENT", "Operational movement required" # specific_id > Order
        LISTING_PRICE_UPDATED = "LISTING_PRICE_UPDATED", "Listing price updated" # specific_id > MarketListedCratePrice

    seen = models.BooleanField(default=False)

    user = models.ForeignKey(
        User,
        verbose_name=_("user"),
        related_name="user_notification",
        on_delete=models.CASCADE,
    )

    date = models.DateTimeField(auto_now=True)

    event_type = models.CharField(max_length=32, choices=NotificationType.choices)

    # NOTE:
    # This seems to be a polymorphic relation, but without the relation model definition.
    # Instead, the original author of this model used the event_type field to determine the entity tha this relates to.
    # In our additions to the NotificationType, we've added which entity relates to this notification event_type.
    specific_id = models.IntegerField(default=None, null=True)

    @staticmethod
    @transaction.atomic
    def notify_cooling_unit_operators(cooling_unit, **kargs):
        users = User.objects.filter(
            cooling_unit_operators=cooling_unit
        ).distinct()

        return Notification.notify_users(users=users, **kargs)

    @staticmethod
    @transaction.atomic
    def notify_cooling_unit_service_providers(cooling_unit, **kargs):
        users = User.objects.filter(
            service_provider__company__location__cooling_units=cooling_unit
        ).distinct()

        return Notification.notify_users(users=users, **kargs)

    @staticmethod
    @transaction.atomic
    def notify_users(users, **kargs):
        notifications = []

        for user in users:
            notification = Notification.objects.create(
                user=user,
                **kargs
            )

            notifications.append(notification)

        return notifications
