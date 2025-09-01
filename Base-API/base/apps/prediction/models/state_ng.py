from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.user.models import Country


class StateNg(models.Model):
    name = models.CharField(_("state_name"), max_length=255)

    country = models.ForeignKey(
        Country,
        verbose_name=_("country"),
        related_name="stateng_country",
        on_delete=models.CASCADE,
    )

    added_by_user = models.BooleanField(default=False)

    def __str__(self):
        return "{} - {}".format(
            self.name,
            self.country,
        )
