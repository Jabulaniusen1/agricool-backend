from django.db import models
from django.utils.translation import gettext_lazy as _
from base.utils.currencies import validate_currency
from .checkout import Checkout

# Constants
STANDARD_FIELD_MAX_LENGTH = 255
CURRENCY_FIELD_MAX_LENGTH = 3
SELLING_UNIT_MAX_LENGTH = 32

class MarketSurvey(models.Model):
    class SellingMetric(models.TextChoices):
        KILOGRAMS = "KILOGRAMS", "Kilograms"
        CRATES = "CRATES", "Crates"
        BAGS = "BAGS", "Bags"
        SACKS = "SACKS", "Sacks"
        BASKETS = "BASKETS", "Baskets"
        BOXES = "BOXES", "Boxes"

    checkout = models.ForeignKey(
        Checkout,
        verbose_name=_("checkout"),
        related_name="survey_checkout",
        on_delete=models.CASCADE,
    )

    selling_place = models.CharField(_("selling_place"), max_length=STANDARD_FIELD_MAX_LENGTH)

    market = models.ForeignKey(
        "prediction.Market",
        verbose_name=_("market"),
        related_name="survey_market",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    price = models.FloatField(_("estimated_price"), default=0)

    currency = models.CharField(
        _("currency"), max_length=CURRENCY_FIELD_MAX_LENGTH, default=None, blank=True, null=True,
        validators=[validate_currency]
    )

    selling_unit = models.CharField(
        max_length=SELLING_UNIT_MAX_LENGTH, choices=SellingMetric.choices, null=True
    )

    selling_date = models.DateTimeField(
        _("selling_date"),
        blank=True,
        null=True,
    )

    # Loss in kg of what was in storage and got spoiled or you were forced to distress sell after check out
    loss = models.PositiveIntegerField(blank=True, null=True)

    kg_in_unit = models.PositiveIntegerField(_("kg_in_unit"), blank=True, null=True)

    class ReasonForLoss(models.TextChoices):
        # not sure if django will turn class names to camel case
        improper_harvest_handling = "Improper handling", "Improper harvest"
        lack_storage_option = "Lack of cold storage", "inappropriate storage"
        overproduction = "Overproduction", "Overproduction"
        transport_damage = "Transportation damage"
        pest_disease = "pest", "disease"
        extreme_weather = "Extreme weather conditions"
        low_market_prices = "market prices too low"
        other_reason = "other"

    reason_for_loss = models.CharField(
        choices=ReasonForLoss.choices, max_length=STANDARD_FIELD_MAX_LENGTH, null=True, blank=True
    )

    crop = models.ForeignKey(
        "storage.Crop",
        related_name="market_survey_crop",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    date_filled_in = models.DateTimeField(
        blank=True,
        null=True,
    )
