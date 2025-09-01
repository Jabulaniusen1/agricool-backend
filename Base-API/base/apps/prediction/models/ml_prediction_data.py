from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.storage.models import Crop

from .market import Market


class MLPredictionData(models.Model):

    market = models.ForeignKey(
        Market,
        verbose_name=_("market"),
        related_name="market_prediction",
        on_delete=models.CASCADE,
    )

    crop = models.ForeignKey(
        Crop,
        verbose_name=_("crop"),
        related_name="crop_prediction",
        on_delete=models.CASCADE,
    )

    # Datetime at which the prediction has been fetched form the API and saved in the Database
    fetched_at = models.DateTimeField(_("fetched_at"), auto_now_add=True)

    # Date of the day for which the predictions have been generated. For example, if reference_date=15/10/2022, then price_forecast_1 will be for 16/10/2022, price_forecast_2 for 17/10/2022, etc...
    reference_date = models.DateField(
        _("reference_date"),
    )

    price_forecast_1 = models.FloatField(_("price_forecast_1"), blank=True, null=True)

    price_forecast_2 = models.FloatField(_("price_forecast_2"), blank=True, null=True)

    price_forecast_3 = models.FloatField(_("price_forecast_3"), blank=True, null=True)

    price_forecast_4 = models.FloatField(_("price_forecast_4"), blank=True, null=True)

    price_forecast_5 = models.FloatField(_("price_forecast_5"), blank=True, null=True)

    price_forecast_6 = models.FloatField(_("price_forecast_6"), blank=True, null=True)

    price_forecast_7 = models.FloatField(_("price_forecast_7"), blank=True, null=True)

    price_forecast_8 = models.FloatField(_("price_forecast_8"), blank=True, null=True)

    price_forecast_9 = models.FloatField(_("price_forecast_9"), blank=True, null=True)

    price_forecast_10 = models.FloatField(_("price_forecast_10"), blank=True, null=True)

    price_forecast_11 = models.FloatField(_("price_forecast_11"), blank=True, null=True)

    price_forecast_12 = models.FloatField(_("price_forecast_12"), blank=True, null=True)

    price_forecast_13 = models.FloatField(_("price_forecast_13"), blank=True, null=True)

    price_forecast_14 = models.FloatField(_("price_forecast_14"), blank=True, null=True)

    only_interpolated_data = models.CharField(
        _("only_interpolated_data"), max_length=255
    )

    def __str__(self):
        return "{}: {} prediction [{}]".format(
            self.market,
            self.crop.name,
            self.fetched_at,
        )
