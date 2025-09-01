from django.db import models
from django.utils.translation import gettext_lazy as _

from .state import State


class Market(models.Model):
    name = models.CharField(_("market_name"), max_length=255)

    state = models.ForeignKey(
        State,
        verbose_name=_("state"),
        related_name="market_state",
        on_delete=models.CASCADE,
    )

    district = models.CharField(_("market_district"), max_length=255)

    used_for_predictions = models.BooleanField(default=False)

    added_by_user = models.BooleanField(default=False)

    def __str__(self):
        return "{} in {}".format(
            self.name,
            self.state,
        )
