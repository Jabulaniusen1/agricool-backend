from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.operation.models.checkout import Checkout

from .crate import Crate

# Default values
DEFAULT_PERCENTAGE = 0
DEFAULT_WEIGHT = 0
DEFAULT_COOLING_FEES = 0

# Constraint limits
MIN_PERCENTAGE = 0
MAX_PERCENTAGE = 1


class CratePartialCheckout(models.Model):
    crate = models.ForeignKey(
        Crate,
        verbose_name=_("crate"),
        related_name="partial_checkouts",
        on_delete=models.CASCADE,
    )
    checkout = models.ForeignKey(
        Checkout,
        verbose_name=_("checkout"),
        related_name="partial_checkouts",
        on_delete=models.CASCADE,
    )

    percentage = models.FloatField(_("percentage"), default=DEFAULT_PERCENTAGE, null=False)
    weight_in_kg = models.PositiveIntegerField(_("weight_in_kg"), default=DEFAULT_WEIGHT)
    cooling_fees = models.FloatField(_("cooling_fees"), default=DEFAULT_COOLING_FEES, null=False)

    class Meta:
        unique_together = ("checkout", "crate")

        # Percentage can only be a number between 0 and 1 (inclusive)
        constraints = [
            models.CheckConstraint(
                check=models.Q(percentage__gte=MIN_PERCENTAGE, percentage__lte=MAX_PERCENTAGE),
                name="checkout_crate_percentage_check",
            ),
        ]
