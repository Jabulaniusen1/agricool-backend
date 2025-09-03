from django.db import models
from django.utils.translation import gettext_lazy as _
from .checkout import Checkout
from .market_survey import MarketSurvey

class MarketsurveyCheckout(models.Model):
    class Meta:
        unique_together = ("checkout", "market_survey")
        db_table = "operation_marketsurvey_checkout"

    checkout = models.ForeignKey(
        Checkout,
        verbose_name=_("checkout"),
        related_name="marketsurveycheckout_checkout",
        on_delete=models.CASCADE,
    )

    market_survey = models.ForeignKey(
        MarketSurvey,
        verbose_name=_("market_survey"),
        related_name="marketsurveycheckout_market_survey",
        on_delete=models.CASCADE,
    )
