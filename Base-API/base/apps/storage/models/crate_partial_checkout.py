from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.operation.models.checkout import Checkout

from .crate import Crate


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

    percentage = models.FloatField(_("percentage"), default=0, null=False)
    weight_in_kg = models.PositiveIntegerField(_("weight_in_kg"), default=0)
    cooling_fees = models.FloatField(_("cooling_fees"), default=0, null=False)

    class Meta:
        unique_together = ("checkout", "crate")

        # Percentage can only be a number between 0 and 1 (inclusive)
        constraints = [
            models.CheckConstraint(
                check=models.Q(percentage__gte=0, percentage__lte=1),
                name="checkout_crate_percentage_check",
            ),
        ]
