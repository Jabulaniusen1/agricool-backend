from django.db import models
from django.utils.translation import gettext_lazy as _

from .state import State

# Field length constants
MARKET_NAME_MAX_LENGTH = 255
MARKET_DISTRICT_MAX_LENGTH = 255

# Default values
DEFAULT_USED_FOR_PREDICTIONS = False
DEFAULT_ADDED_BY_USER = False


class Market(models.Model):
    name = models.CharField(_("market_name"), max_length=MARKET_NAME_MAX_LENGTH)

    state = models.ForeignKey(
        State,
        verbose_name=_("state"),
        related_name="market_state",
        on_delete=models.CASCADE,
    )

    district = models.CharField(_("market_district"), max_length=MARKET_DISTRICT_MAX_LENGTH)

    used_for_predictions = models.BooleanField(default=DEFAULT_USED_FOR_PREDICTIONS)

    added_by_user = models.BooleanField(default=DEFAULT_ADDED_BY_USER)

    def __str__(self):
        return "{} in {}".format(
            self.name,
            self.state,
        )
