from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from base.apps.marketplace.services.order import compute_order_crate_item
from base.apps.storage.models import Crate

from .market_listed_crate import MarketListedCrate
from .order import Order
from .order_pickup_details import OrderPickupDetails


class OrderCrateItem(models.Model):
    """
    Represents an individual order item corresponding to a market listed crate.
    (Docstring as before)
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name=_("items"), related_name='items')
    market_listed_crate = models.ForeignKey(MarketListedCrate, on_delete=models.PROTECT, null=False, verbose_name=_("order_item_market_listed_crate"), related_name='order_items')
    resulting_crates = models.ManyToManyField(Crate, verbose_name=_("resulting_crates"), related_name='ref_order_items')
    
    # User choices
    ordered_entire_crate = models.BooleanField(_("ordered_entire_crate"), default=False)
    ordered_produce_weight = models.FloatField(_("ordered_produce_weight"), default=0)
    coupon = models.ForeignKey('Coupon', on_delete=models.PROTECT, null=True, blank=True)
    
    # Time-frozen values
    frozen_crate_available_weight = models.FloatField(_("frozen_crate_available_weight"), default=0)
    frozen_produce_price_per_kg = models.FloatField(_("frozen_produce_price_per_kg"), default=0)
    
    # Computed fields
    cmp_last_updated_at = models.DateTimeField(_("cmp_last_updated_at"), null=True, blank=True)
    cmp_produce_amount = models.FloatField(_("cmp_produce_amount"), default=0)
    cmp_cooling_fees_amount = models.FloatField(_("cmp_cooling_fees_amount"), default=0)
    cmp_discount_amount = models.FloatField(_("cmp_discount_amount"), default=0)
    cmp_total_amount = models.FloatField(_("cmp_total_amount"), default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['order'], name='quicker_order_items_lookup'),
            models.Index(fields=['coupon'], name='quicker_coupon_lookup'),
        ]
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        OrderPickupDetails.clear_unused_pickup_details(self.order)
    
    @transaction.atomic
    def compute(self, save=True, compute_dependencies=True):
        """
        Delegates computation of pricing details to a service function.
        """
        # Only compute if the order is in CART status.
        if self.order.status != Order.Status.CART:
            if save:
                self.save()
            return
        
        # Delegate computation and receive a dictionary of computed values.
        computed = compute_order_crate_item(self, compute_dependencies=compute_dependencies)
        
        # Update model fields from the computed values.
        self.ordered_produce_weight = computed['ordered_produce_weight']
        self.frozen_produce_price_per_kg = computed['frozen_produce_price_per_kg']
        self.frozen_crate_available_weight = computed['frozen_crate_available_weight']
        self.ordered_entire_crate = computed['ordered_entire_crate']
        self.cmp_last_updated_at = computed['cmp_last_updated_at']
        self.cmp_produce_amount = computed['cmp_produce_amount']
        self.cmp_discount_amount = computed['cmp_discount_amount']
        self.cmp_cooling_fees_amount = computed['cmp_cooling_fees_amount']
        self.cmp_total_amount = computed['cmp_total_amount']
    
        if save:
            self.save()
    
    def __str__(self):
        return f"OrderCrateItem in Order {self.order.id} for Market Listing {self.market_listed_crate}"
