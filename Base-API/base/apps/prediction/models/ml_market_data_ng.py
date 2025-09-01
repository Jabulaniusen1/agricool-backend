from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.storage.models import Crop

from .state_ng import StateNg


class MLMarketDataNigeria(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["-date"], name="mlmarketdatanigeria_date_desc"),
        ]

    crop = models.ForeignKey(
        Crop,
        verbose_name=_("crop"),
        related_name="crop_market_data_ng",
        on_delete=models.CASCADE,
    )

    state = models.ForeignKey(
        StateNg,
        verbose_name=_("stateng"),
        related_name="stateng_market_data",
        on_delete=models.CASCADE,
    )

    date = models.DateField(
        _("date"),
    )

    state_label = models.IntegerField(
        _("state_label"),
    )

    commodity_label = models.IntegerField(
        _("commodity_label"),
    )

    price = models.FloatField(
        _("price"),
    )

    last_price_1m = models.FloatField(
        _("last_price_1m"),
    )

    last_price_2m = models.FloatField(
        _("last_price_2m"),
    )

    last_price_3m = models.FloatField(
        _("last_price_3m"),
    )

    last_price_4m = models.FloatField(
        _("last_price_4m"),
    )

    last_price_5m = models.FloatField(
        _("last_price_5m"),
    )

    usd_to_ngn = models.FloatField(
        _("usd_to_ngn"),
    )

    state_rollup = models.FloatField(
        _("state_rollup"),
    )
    cpi = models.FloatField(
        _("cpi"),
    )
