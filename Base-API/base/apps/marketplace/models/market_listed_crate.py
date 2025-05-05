from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.apps.operation.services.checkout import \
    get_total_due_in_cooling_fees_per_kg
from base.apps.storage.models import Crate
from base.utils.currencies import validate_currency

from .order import Order


class MarketListedCrate(models.Model):
    """
    Represents a crate listing in the marketplace.
    
    This model links a Crate instance with a marketplace listing,
    and tracks computed metrics such as pending cooling fees,
    locked weight from pending orders, and available weight.
    
    An active listing is one that has not been delisted (i.e., `delisted_at` is null).
    """

    created_at = models.DateTimeField(_("created_at"), auto_now_add=True)
    delisted_at = models.DateTimeField(_("delisted_at"), null=True, blank=True)  # Allow null/blank for active listings
    crate = models.ForeignKey(Crate, on_delete=models.CASCADE, related_name='market_listed_crates')
    currency = models.CharField(_("currency"), max_length=3, default="NGN", validators=[validate_currency])

    # Computed fields
    cmp_last_updated_at = models.DateTimeField(_("cmp_last_updated_at"), null=True, blank=True)
    cmp_pending_in_cooling_fees = models.FloatField(_("cmp_pending_in_cooling_fees"), default=0)
    cmp_pending_in_cooling_fees_price_per_kg = models.FloatField(_("cmp_pending_in_cooling_fees_price_per_kg"), default=0)
    cmp_weight_locked_in_payment_pending_orders_in_kg = models.FloatField(_("cmp_weight_locked_in_payment_pending_orders_in_kg"), default=0)
    cmp_available_weight_in_kg = models.FloatField(_("cmp_available_weight_in_kg"), default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['crate'], condition=models.Q(delisted_at__isnull=True), name='unique_active_listing_per_crate')
        ]

    @transaction.atomic
    def compute(self, save=True):
        """
        Computes and updates the following fields:
          - cmp_pending_in_cooling_fees_price_per_kg: total due in cooling fees per kg for the crate.
          - cmp_pending_in_cooling_fees: total pending cooling fees for the crate.
          - cmp_weight_locked_in_payment_pending_orders_in_kg: total weight in kg locked in pending orders.
          - cmp_available_weight_in_kg: crate weight minus the locked weight.
        
        Raises:
            ValidationError: If the crate's currency does not match the market listed crate currency.
        """
        crate = self.crate

        # Stock management - Compute total ordered weight in locked orders
        ordered_items_aggregation_result = self.order_items.filter(
            order__status=Order.Status.PAYMENT_PENDING
        ).aggregate(
            total_weight=Sum('ordered_produce_weight')
        )

        if crate.currency != self.currency:
            raise ValidationError("Crate currency does not match market listed crate currency")

        crate_weight = crate.weight
        pending_in_cooling_fees_price_per_kg = get_total_due_in_cooling_fees_per_kg(crate)

        ##
        # Safe to replace values and save
        ##
        self.cmp_last_updated_at = timezone.now()
        self.cmp_pending_in_cooling_fees_price_per_kg = pending_in_cooling_fees_price_per_kg
        self.cmp_pending_in_cooling_fees = pending_in_cooling_fees_price_per_kg * crate_weight

        total_locked_weight = ordered_items_aggregation_result.get('total_weight') or 0
        self.cmp_weight_locked_in_payment_pending_orders_in_kg = max(0, total_locked_weight)
        self.cmp_available_weight_in_kg = max(0, crate_weight - self.cmp_weight_locked_in_payment_pending_orders_in_kg)


        if save:
            self.save()

    def __str__(self):
        return f"MarketListedCrate {self.id} for Crate {self.crate}"
