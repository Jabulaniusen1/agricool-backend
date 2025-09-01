from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.storage.models import Crop

from .market import Market


class MLMarketDataIndia(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["-date"], name="mlmarketdataindia_date_desc"),
        ]

    market = models.ForeignKey(
        Market,
        verbose_name=_("market"),
        related_name="market_market_data",
        on_delete=models.CASCADE,
    )

    crop = models.ForeignKey(
        Crop,
        verbose_name=_("crop"),
        related_name="crop_market_data",
        on_delete=models.CASCADE,
    )

    date = models.DateField(
        _("date"),
    )

    state_label = models.IntegerField(
        _("state_label"),
    )

    district_label = models.IntegerField(
        _("district_label"),
    )

    market_label = models.IntegerField(
        _("market_label"),
    )

    commodity_label = models.IntegerField(
        _("commodity_label"),
    )

    arrivals_metric_tons = models.FloatField(
        _("arrivals_metric_tons"),
    )

    modal_price_rs_per_quintal = models.FloatField(
        _("modal_price_rs_per_quintal"),
    )

    last_price_1d = models.FloatField(
        _("last_price_1d"),
    )

    last_price_2d = models.FloatField(
        _("last_price_2d"),
    )

    last_price_3d = models.FloatField(
        _("last_price_3d"),
    )

    last_price_4d = models.FloatField(
        _("last_price_4d"),
    )

    last_price_5d = models.FloatField(
        _("last_price_5d"),
    )

    last_price_6d = models.FloatField(
        _("last_price_6d"),
    )

    last_price_7d = models.FloatField(
        _("last_price_7d"),
    )

    week = models.IntegerField(
        _("week"),
    )

    day = models.IntegerField(
        _("day"),
    )

    month = models.IntegerField(
        _("month"),
    )

    usd_to_inr = models.FloatField(
        _("usd_to_inr"),
    )

    brent_oil_price = models.FloatField(
        _("brent_oil_price"),
    )

    state_rollup = models.FloatField(
        _("state_rollup"),
    )

    district_rollup = models.FloatField(
        _("district_rollup"),
    )

    availability = models.FloatField(
        _("availability"),
    )

    price_available = models.BooleanField(
        _("price_available"),
    )

    price_available_1d = models.BooleanField(
        _("price_available_1d"),
    )

    price_available_2d = models.BooleanField(
        _("price_available_2d"),
    )

    price_available_3d = models.BooleanField(
        _("price_available_3d"),
    )

    price_available_4d = models.BooleanField(
        _("price_available_4d"),
    )

    price_available_5d = models.BooleanField(
        _("price_available_5d"),
    )

    price_available_6d = models.BooleanField(
        _("price_available_6d"),
    )

    price_available_7d = models.BooleanField(
        _("price_available_7d"),
    )

    usd_to_inr_1d = models.FloatField(
        _("usd_to_inr_1d"),
    )

    usd_to_inr_2d = models.FloatField(
        _("usd_to_inr_2d"),
    )

    usd_to_inr_3d = models.FloatField(
        _("usd_to_inr_3d"),
    )

    usd_to_inr_4d = models.FloatField(
        _("usd_to_inr_4d"),
    )

    usd_to_inr_5d = models.FloatField(
        _("usd_to_inr_5d"),
    )

    usd_to_inr_6d = models.FloatField(
        _("usd_to_inr_6d"),
    )

    usd_to_inr_7d = models.FloatField(
        _("usd_to_inr_7d"),
    )

    usd_to_inr_8d = models.FloatField(
        _("usd_to_inr_8d"),
    )

    usd_to_inr_9d = models.FloatField(
        _("usd_to_inr_9d"),
    )

    usd_to_inr_10d = models.FloatField(
        _("usd_to_inr_10d"),
    )

    usd_to_inr_11d = models.FloatField(
        _("usd_to_inr_11d"),
    )

    usd_to_inr_12d = models.FloatField(
        _("usd_to_inr_12d"),
    )

    usd_to_inr_13d = models.FloatField(
        _("usd_to_inr_13d"),
    )

    usd_to_inr_14d = models.FloatField(
        _("usd_to_inr_14d"),
    )

    usd_to_inr_lag = models.FloatField(
        _("usd_to_inr_lag"),
    )

    brent_oil_price_1d = models.FloatField(
        _("brent_oil_price_1d"),
    )

    brent_oil_price_2d = models.FloatField(
        _("brent_oil_price_2d"),
    )

    brent_oil_price_3d = models.FloatField(
        _("brent_oil_price_3d"),
    )

    brent_oil_price_4d = models.FloatField(
        _("brent_oil_price_4d"),
    )

    brent_oil_price_5d = models.FloatField(
        _("brent_oil_price_5d"),
    )

    brent_oil_price_6d = models.FloatField(
        _("brent_oil_price_6d"),
    )

    brent_oil_price_7d = models.FloatField(
        _("brent_oil_price_7d"),
    )

    brent_oil_price_8d = models.FloatField(
        _("brent_oil_price_8d"),
    )

    brent_oil_price_9d = models.FloatField(
        _("brent_oil_price_9d"),
    )

    brent_oil_price_10d = models.FloatField(
        _("brent_oil_price_10d"),
    )

    brent_oil_price_11d = models.FloatField(
        _("brent_oil_price_11d"),
    )

    brent_oil_price_12d = models.FloatField(
        _("brent_oil_price_12d"),
    )

    brent_oil_price_13d = models.FloatField(
        _("brent_oil_price_13d"),
    )

    brent_oil_price_14d = models.FloatField(
        _("brent_oil_price_14d"),
    )

    brent_oil_price_lag = models.FloatField(
        _("brent_oil_price_lag"),
    )

    availability_bit = models.FloatField(
        _("availability_bit"),
    )
