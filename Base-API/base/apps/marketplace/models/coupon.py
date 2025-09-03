from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.apps.user.models import Company, User

# Constants
COUPON_CODE_MAX_LENGTH = 25
MIN_DISCOUNT_PERCENTAGE = 0
MAX_DISCOUNT_PERCENTAGE = 1
DEFAULT_DISCOUNT_PERCENTAGE = 0


class Coupon(models.Model):
    """
    Represents a discount coupon that can be used by users.
    
    Coupons are created by a user, and can be owned by a specific user or on behalf of a company.
    A coupon is valid if it has not been revoked. The discount is expressed as a percentage,
    which should be between 0 and 1 (exclusive).
    """
    
    created_at = models.DateTimeField(_("created_at"), auto_now_add=True)
    revoked_at = models.DateTimeField(_("revoked_at"), null=True, blank=True)

    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_coupons')
    owned_by_user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='own_coupons')
    owned_on_behalf_of_company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True, related_name='own_coupons')

    code = models.CharField(_("code"), max_length=COUPON_CODE_MAX_LENGTH)
    discount_percentage = models.FloatField(_("discount_percentage"), default=DEFAULT_DISCOUNT_PERCENTAGE)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(discount_percentage__gt=MIN_DISCOUNT_PERCENTAGE, discount_percentage__lt=MAX_DISCOUNT_PERCENTAGE), name='valid_discount_percentage'),
            models.UniqueConstraint(fields=['created_by_user', 'code'], condition=models.Q(revoked_at__isnull=True), name='unique_valid_coupon_per_user')
        ]

    def revoke(self):
        """
        Revokes the coupon by setting the revoked_at field to the current time.
        This marks the coupon as invalid.
        """
        self.revoked_at = timezone.now()
        self.save()

    def is_valid(self):
        """
        Returns True if the coupon has not been revoked; otherwise, False.
        """
        return self.revoked_at is None

    def __str__(self):
        user_display = self.owned_by_user or "No User"
        return f"Coupon {self.code} for user {user_display}"
