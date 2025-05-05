from django.db import models
from django.utils.translation import gettext_lazy as _
from base.utils.currencies import validate_currency
from .farmer_survey import FarmerSurvey

class FarmerSurveyCommodity(models.Model):
    class SellingMetric(models.TextChoices):
        KILOGRAMS = "KILOGRAMS", "Kilograms"
        CRATES = "CRATES", "Crates"
        BAGS = "BAGS", "Bags"
        SACKS = "SACKS", "Sacks"
        BASKETS = "BASKETS", "Baskets"

    class ReasonForLoss(models.TextChoices):
        # not sure if django will turn class names to camel case
        improper_harvest_handling = "Improper handling", "Improper harvest"
        lack_storage_option = "Lack of cold storage", "inappropriate storage"
        overproduction = "Overproduction", "overproduction"
        transport_damage = "Transportation damage"
        pest_disease = "pest", "disease"
        extreme_weather = ("Extreme weather conditions",)
        low_market_prices = "market prices too low"
        other_reason = "other"

    farmer_survey = models.ForeignKey(
        FarmerSurvey,
        verbose_name=_("farmer_survey"),
        related_name="commodity_farmer_survey",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    crop = models.ForeignKey(
        "storage.Crop",
        verbose_name=_("crop"),
        related_name="crop_farmer_survey",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    average_price = models.PositiveSmallIntegerField(blank=True, null=True)

    unit = models.CharField(
        max_length=32, choices=SellingMetric.choices, blank=True, null=True
    )

    # Total quantity produced in a season (kg)
    quantity_total = models.FloatField(blank=True, null=True)

    # Self-consumed (kg) of the total quantity produced in a season
    quantity_self_consumed = models.FloatField(blank=True, null=True)

    # Sold (kg) of the total quantity produced in a season
    quantity_sold = models.FloatField(blank=True, null=True)

    # Lost or sold below market price (kg) of the total quantity produced in a season
    quantity_below_market_price = models.FloatField(blank=True, null=True)

    # How many months is an average season
    average_season_in_months = models.PositiveIntegerField(blank=True, null=True)

    currency = models.CharField(
        _("currency"), max_length=3, default=None, blank=True, null=True,
        validators=[validate_currency]
    )

    kg_in_unit = models.PositiveIntegerField(_("kg_in_unit"), blank=True, null=True)

    reason_for_loss = models.CharField(
        choices=ReasonForLoss.choices, max_length=255, null=True, blank=True
    )

    date_filled_in = models.DateTimeField(
        blank=True,
        null=True,
    )

    date_last_modified = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name_plural = "farmer survey commodities"
