from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.user.models import User

from .market_listed_crate import MarketListedCrate


class MarketListedCratePrice(models.Model):
    """
    Represents the price details for a market listed crate.
    
    This model stores the pricing information associated with a market listed crate,
    including the price per kilogram for the produce and metadata such as the creator
    of the record (either an operator or a cooling user) and the creation timestamp.
    """
    
    created_at = models.DateTimeField(_("created_at"), auto_now_add=True)
    created_by_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='market_listing_crate_prices')
    produce_price_per_kg = models.FloatField(_("produce_price_per_kg"), default=0)
    market_listed_crate = models.ForeignKey(MarketListedCrate, on_delete=models.CASCADE, related_name='prices')

    class Meta:
        constraints = []
