from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.utils.currencies import validate_currency

from .movement import Movement


class Checkout(models.Model):
    class PaymentThrough(models.TextChoices):
        DIRECT = "DIRECT", "Direct"
        COLDTIVATE = "COLDTIVATE", "Coldtivate app"

    class PaymentGateway(models.TextChoices):
        PAYTACK = "PAYTACK", "Paystack"
        STRIPE = "STRIPE", "Stripe"

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CREDIT_CARD = "CREDIT_CARD", "Credit card"
        QR_CODE = "QR_CODE", "QR Code"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        USSD = "USSD", "USSD"
        OPAY = "OPAY", "Opay"
        UPI = "UPI", "UPI"


    payment_through = models.CharField(
        max_length=20,
        choices=PaymentThrough.choices,
        default=None,
        blank=True,
        null=True,
    )
    payment_gateway = models.CharField(
        max_length=20,
        choices=PaymentGateway.choices,
        default=None,
        blank=True,
        null=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=None,
        blank=True,
        null=True,
    )

    movement = models.ForeignKey(
        Movement,
        verbose_name=_("movement"),
        related_name="checkouts",
        on_delete=models.CASCADE,
    )

    currency = models.CharField(
        _("currency"), max_length=3, default=None, blank=True, null=True,
        validators=[validate_currency]
    )
    discount_amount = models.FloatField(_("discount_amount"), default=0)
    paid = models.BooleanField(_("paid"))

    # Computed fields
    cmp_last_updated_at = models.DateTimeField(_("cmp_last_updated_at"), null=True, blank=True)
    cmp_total_cooling_fees_amount = models.FloatField(_("cmp_total_cooling_fees_amount"), default=0)
    cmp_total_amount = models.FloatField(_("cmp_total_amount"), default=0)

    def compute(self, save=True, compute_dependencies=True):
        self.cmp_last_updated_at = timezone.now()
        self.cmp_total_cooling_fees_amount = self.partial_checkouts.aggregate(
            total_paid_in_cooling_fees=models.Sum('cooling_fees')
        )['total_paid_in_cooling_fees'] or 0

        self.cmp_total_amount = self.cmp_total_cooling_fees_amount - (self.discount_amount or 0)

        if save:
            self.save()
