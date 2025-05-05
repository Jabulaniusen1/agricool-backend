from django.db import models
from django.utils.translation import gettext_lazy as _


class Pricing(models.Model):
    class PricingType(models.TextChoices):
        FIXED = "FIXED", "Fixed"
        PERIODICITY = "PERIODICITY", "Periodicity"

    pricing_type = models.CharField(max_length=32, choices=PricingType.choices)

    fixed_rate = models.FloatField(_("fixed_rate"), blank=True)

    daily_rate = models.FloatField(_("daily_rate"), blank=True)
