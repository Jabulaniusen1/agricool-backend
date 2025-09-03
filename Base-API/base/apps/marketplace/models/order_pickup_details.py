from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.storage.models import CoolingUnit

from .order import Order

# Constants
PICKUP_METHOD_MAX_LENGTH = 16


class OrderPickupDetails(models.Model):
    """
    Stores the pickup details for a given order in relation to a specific cooling unit.
    
    This model captures the chosen pickup method for an order, ensuring that there is only one
    pickup detail per order and cooling unit combination. This is useful for managing the different
    ways an order can be picked up, such as same-day pick-up, storage, or delivery.
    """
    class PickUpMethod(models.TextChoices):
        PICK_UP_SAME_DAY = 'pick-up-same-day', _('Pick Up in the same day')
        KEEP_IN_STORAGE = 'keep-in-storage', _('Keep in storage')
        DELIVERY = 'delivery', _('Delivery')

    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name=_("pickup_details"), related_name='pickup_details')
    cooling_unit = models.ForeignKey(CoolingUnit, on_delete=models.PROTECT, null=False, verbose_name=_("order_item_pickup_details"), related_name='order_item_pickup_details')
    pickup_method = models.CharField(_("pickup_method"), max_length=PICKUP_METHOD_MAX_LENGTH, null=False, blank=False, choices=PickUpMethod.choices)

    class Meta:
        indexes = [
            models.Index(fields=['order'], name='quicker_order_pickup_lookup'), # for quicker carts and order endpoints
        ]
        constraints = [
            models.UniqueConstraint(fields=['order', 'cooling_unit'], name='only_one_per_cooling_unit_and_order'),
        ]

    @staticmethod
    def clear_unused_pickup_details(order):
        cooling_unit_ids = order.get_cooling_unit_ids()
        OrderPickupDetails.objects.filter(order=order).exclude(cooling_unit_id__in=cooling_unit_ids).delete()
