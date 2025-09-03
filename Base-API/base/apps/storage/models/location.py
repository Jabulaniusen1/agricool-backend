from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.apps.user.models import Company

# Field length constants
LOCATION_NAME_MAX_LENGTH = 255
STATE_MAX_LENGTH = 255
CITY_MAX_LENGTH = 255
STREET_MAX_LENGTH = 255
ZIP_CODE_MAX_LENGTH = 255

# Default values
DEFAULT_DELETED = False


class Location(models.Model):
    name = models.CharField(_("name"), max_length=LOCATION_NAME_MAX_LENGTH, blank=True, null=True)

    state = models.CharField(_("state"), max_length=STATE_MAX_LENGTH, blank=True)
    city = models.CharField(_("city"), max_length=CITY_MAX_LENGTH, blank=True)
    street = models.CharField(_("street"), max_length=STREET_MAX_LENGTH, blank=True)
    street_number = models.IntegerField(_("street_number"), blank=True, null=True)
    zip_code = models.CharField(_("zipCode"), max_length=ZIP_CODE_MAX_LENGTH, blank=True)
    point = gis_models.PointField(geography=True, null=False, blank=False)

    company = models.ForeignKey(
        Company,
        verbose_name=_("company"),
        related_name="location_provider_company",
        on_delete=models.CASCADE,
        null=True,
    )

    deleted = models.BooleanField(default=DEFAULT_DELETED)

    date_creation = models.DateTimeField(
        blank=True,
        null=True,
    )

    date_last_modified = models.DateTimeField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return "{} {}, {}, {}, {}".format(
            self.street,
            self.street_number,
            self.zip_code,
            self.city,
            self.state,
        )
