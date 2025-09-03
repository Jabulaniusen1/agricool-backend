from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.user.models import Country

# Field length constants
STATE_NAME_MAX_LENGTH = 255

# Default values
DEFAULT_ADDED_BY_USER = False


class StateNg(models.Model):
    name = models.CharField(_("state_name"), max_length=STATE_NAME_MAX_LENGTH)

    country = models.ForeignKey(
        Country,
        verbose_name=_("country"),
        related_name="stateng_country",
        on_delete=models.CASCADE,
    )

    added_by_user = models.BooleanField(default=DEFAULT_ADDED_BY_USER)

    def __str__(self):
        return "{} - {}".format(
            self.name,
            self.country,
        )
