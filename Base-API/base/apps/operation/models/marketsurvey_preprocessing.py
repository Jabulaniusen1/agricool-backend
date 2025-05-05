from django.db import models
from django.utils.translation import gettext_lazy as _
from base.apps.user.models import Farmer, Operator

class MarketsurveyPreprocessing(models.Model):

    operator = models.ForeignKey(
        Operator,
        verbose_name=_("operator"),
        related_name="marketsurvey_preprocess_operator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    farmer = models.ForeignKey(
        Farmer,
        verbose_name=_("farmer"),
        related_name="marketsurvey_preprocess_farmer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    crop = models.ForeignKey(
        "storage.Crop",
        related_name="marketsurvey_preprocess_crop",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    checkout = models.ForeignKey(
        "operation.Checkout",
        verbose_name=_("checkout"),
        related_name="marketsurvey_preprocess_checkout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(_("is_active"), default=True)

    checkout_at = models.DateTimeField()
    modified_at = models.DateTimeField(auto_now=True)
