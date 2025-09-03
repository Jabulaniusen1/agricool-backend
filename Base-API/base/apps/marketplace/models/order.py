from decimal import ROUND_HALF_UP

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.apps.marketplace.payment_processor.paystack.fees import \
    calculate_final_amount_and_paystack_fees_from_subtotal_amount
from base.apps.marketplace.services.order import (
    clear_coupon_code_service, process_coupon_code, process_order_completion,
    validate_order_payment_conditions)
from base.apps.user.models import Company, Operator, ServiceProvider, User
from base.settings import MARKETPLACE_COLDTIVATE_EXPONENT
from base.utils.currencies import quantitize_float, validate_currency

# Constants
PAYMENT_REFERENCE_MAX_LENGTH = 12
CURRENCY_FIELD_MAX_LENGTH = 3
PAYSTACK_SPLIT_CODE_MAX_LENGTH = 16
DEFAULT_CURRENCY = "NGN"


class Order(models.Model):
    class Status(models.TextChoices):
        CART = 'cart', _('Cart')
        ABANDONED_CART = 'abandoned-cart', _('Abandoned Cart')
        PAYMENT_PENDING = 'payment-pending', _('Payment Pending')
        PAYMENT_EXPIRED = 'payment-expired', _('Payment Expired')
        PAID = 'paid', _('Paid')
        CANCELLED = 'cancelled', _('Cancelled')

    status = models.CharField(_("status"), max_length=20, choices=Status.choices, default=Status.CART)
    status_changed_at = models.DateTimeField(_("status_changed_at"), auto_now=True)
    payment_references = ArrayField(
        models.CharField(_("payment_reference"), max_length=PAYMENT_REFERENCE_MAX_LENGTH, null=True),
        default=list,
        blank=True,
        null=False,
    )
    created_at = models.DateTimeField(_("created_at"), auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    owned_on_behalf_of_company = models.ForeignKey(
        Company, on_delete=models.PROTECT, null=True, blank=True, related_name='orders'
    )
    currency = models.CharField(_("currency"), max_length=CURRENCY_FIELD_MAX_LENGTH, default=DEFAULT_CURRENCY, validators=[validate_currency])

    # Payment related
    paystack_split_code = models.CharField(_("paystack_split_code"), max_length=PAYSTACK_SPLIT_CODE_MAX_LENGTH, null=True, blank=True)
    paid_at = models.DateTimeField(_("paid_at"), null=True, blank=True)
    amount_paid = models.FloatField(_("amount_paid"), default=0)

    # Computed fields
    cmp_last_updated_at = models.DateTimeField(_("cmp_last_updated_at"), null=True, blank=True)
    cmp_total_produce_amount = models.FloatField(_("cmp_total_produce_amount"), default=0)
    cmp_total_cooling_fees_amount = models.FloatField(_("cmp_total_cooling_fees_amount"), default=0)
    cmp_total_coldtivate_amount = models.FloatField(_("cmp_total_coldtivate_amount"), default=0)
    cmp_total_discount_amount = models.FloatField(_("cmp_total_discount_amount"), default=0)
    cmp_total_payment_fees_amount = models.FloatField(_("cmp_total_payment_fees_amount"), default=0)
    cmp_total_amount = models.FloatField(_("cmp_total_amount"), default=0)

    class Meta:
        indexes = [
            models.Index(
                fields=['created_by_user', 'status'],
                name='quicker_user_order_lookup',
            ),
        ]

    def clean(self):
        """
        Validates the order based on business rules. For example, if an order is a cart
        and was created on behalf of a company, ensure that the user is still connected.
        """
        super().clean()

        if self.status == self.Status.CART and self.owned_on_behalf_of_company:
            if (
                not ServiceProvider.is_employee_of_company(self.created_by_user, self.owned_on_behalf_of_company)
                and not Operator.is_operator_of_company(self.created_by_user, self.owned_on_behalf_of_company)
            ):
                raise ValidationError(_('The user is not connected to the company.'))

    def _ensure_status(self, status):
        """
        Ensure that the order is in the expected status.
        """
        if self.status != status:
            raise ValidationError(
                _("The order status was expected to be %s, although it is currently %s.") % (status, self.status)
            )

    @transaction.atomic
    def abandon_cart(self):
        """
        Abandon a cart order by updating the status.
        """
        self._ensure_status(Order.Status.CART)
        self.status = Order.Status.ABANDONED_CART
        self.status_changed_at = timezone.now()
        self.save()

    @transaction.atomic
    def apply_coupon_code(self, coupon_code):
        """
        Apply a coupon code to eligible order items.
        """
        self._ensure_status(Order.Status.CART)
        process_coupon_code(order=self, coupon_code=coupon_code)
        self.compute(save=True)

    @transaction.atomic
    def clear_coupon_code(self, coupon_code):
        """
        Remove a coupon code from eligible order items.
        """
        self._ensure_status(Order.Status.CART)
        clear_coupon_code_service(order=self, coupon_code=coupon_code)
        self.compute(save=True)

    @transaction.atomic
    def cancel_payment_pending_order(self):
        """
        Cancel an order that is pending payment.
        """
        self._ensure_status(Order.Status.PAYMENT_PENDING)
        self.status = Order.Status.CANCELLED
        self.status_changed_at = timezone.now()
        self.compute(save=True)

        for item in self.items.all():
            market_listing_crate = item.market_listed_crate
            if market_listing_crate.delisted_at is None:
                market_listing_crate.compute(save=True)

    @transaction.atomic
    def expire_payment_pending_order(self):
        """
        Mark a payment pending order as expired.
        """
        self._ensure_status(Order.Status.PAYMENT_PENDING)
        self.status = Order.Status.PAYMENT_EXPIRED
        self.status_changed_at = timezone.now()
        self.save()
        self.compute(save=True)

    @transaction.atomic
    def complete_payment_pending_order(self, payment_through=None, payment_gateway=None, payment_method=None):
        """
        Complete a payment pending order by processing all related operations such as
        creating movements, checkouts, checkins, allocating crates, and sending notifications.
        """
        self._ensure_status(Order.Status.PAYMENT_PENDING)
        process_order_completion(
            order=self,
            payment_through=payment_through,
            payment_gateway=payment_gateway,
            payment_method=payment_method,
        )

    def check_if_valid_to_proceed_to_payment(self):
        """
        Validates various conditions before proceeding to payment.
        """
        validate_order_payment_conditions(order=self)

    def get_cooling_unit_ids(self):
        """
        Returns the distinct cooling unit IDs linked to this order's items.
        """
        from base.apps.storage.models.cooling_unit import CoolingUnit

        crates_ids = self.items.annotate(crate_id=F('market_listed_crate__crate_id')).values_list('crate_id', flat=True)
        cooling_units_ids = CoolingUnit.objects.filter(
            crate_cooling_unit__in=crates_ids
        ).distinct('id').values_list('id', flat=True)
        return cooling_units_ids

    @transaction.atomic
    def compute(self, save=True, compute_dependencies=True):
        """
        Recalculate order totals and fees based on its items.
        """
        if self.status != Order.Status.CART:
            if save:
                self.save()
            return

        total_produce_amount = 0
        total_cooling_fees_amount = 0
        total_discount_amount = 0
        subtotal_amount = 0

        for order_crate_item in self.items.all():
            if compute_dependencies:
                order_crate_item.compute(save=save)

            if order_crate_item.ordered_produce_weight == 0:
                if self.status == Order.Status.CART:
                    order_crate_item.delete()
                continue

            total_produce_amount += order_crate_item.cmp_produce_amount
            total_cooling_fees_amount += order_crate_item.cmp_cooling_fees_amount
            total_discount_amount += order_crate_item.cmp_discount_amount
            subtotal_amount += order_crate_item.cmp_total_amount

        total_produce_amount = quantitize_float(total_produce_amount, self.currency, rounding=ROUND_HALF_UP)
        total_cooling_fees_amount = quantitize_float(total_cooling_fees_amount, self.currency, rounding=ROUND_HALF_UP)
        total_discount_amount = quantitize_float(total_discount_amount, self.currency, rounding=ROUND_HALF_UP)
        total_coldtivate_amount = quantitize_float(
            subtotal_amount * MARKETPLACE_COLDTIVATE_EXPONENT, self.currency, rounding=ROUND_HALF_UP
        )
        subtotal_amount = quantitize_float(subtotal_amount + total_coldtivate_amount, self.currency, rounding=ROUND_HALF_UP)

        final_amount, total_payment_fees_amount = calculate_final_amount_and_paystack_fees_from_subtotal_amount(
            subtotal_amount
        )

        self.cmp_last_updated_at = timezone.now()
        self.cmp_total_produce_amount = max(total_produce_amount, 0)
        self.cmp_total_cooling_fees_amount = max(total_cooling_fees_amount, 0)
        self.cmp_total_coldtivate_amount = max(total_coldtivate_amount, 0)
        self.cmp_total_discount_amount = max(total_discount_amount, 0)
        self.cmp_total_payment_fees_amount = max(total_payment_fees_amount, 0)
        self.cmp_total_amount = max(final_amount, 0)

        if save:
            self.save()

    def __str__(self):
        return f"Order {self.id} by {self.created_by_user}"
