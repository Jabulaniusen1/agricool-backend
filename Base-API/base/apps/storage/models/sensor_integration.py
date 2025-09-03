from django.db import models
from django.utils.translation import gettext_lazy as _
from django_cryptography.fields import encrypt

from .cooling_unit import CoolingUnit

# Field length constants
SENSOR_TYPE_MAX_LENGTH = 16
USERNAME_MAX_LENGTH = 150
PASSWORD_MAX_LENGTH = 150
SOURCE_ID_MAX_LENGTH = 64

# Default values
DEFAULT_PASSWORD = ""


class SensorIntegration(models.Model):
    class SensorType(models.TextChoices):
        VICTRON = 'victron', _('Victron Energy')
        UBIBOT = 'ubibot', _('Ubibot')
        FIGORR = 'figorr', _('Figorr')
        ECOZEN = 'ecozen', _('Ecozen')

    cooling_unit = models.ForeignKey(
        CoolingUnit,
        verbose_name=_("cooling_unit"),
        related_name="sensor_user_cooling_unit",
        on_delete=models.SET_NULL,
        null=True,
    )

    type = models.CharField(_("type"), max_length=SENSOR_TYPE_MAX_LENGTH, null=False, blank=False, choices=SensorType.choices)

    username = models.CharField(max_length=USERNAME_MAX_LENGTH, blank=True)
    password = encrypt(models.CharField(max_length=PASSWORD_MAX_LENGTH, default=DEFAULT_PASSWORD, blank=True))
    source_id = models.CharField(max_length=SOURCE_ID_MAX_LENGTH, blank=True)

    date_sensor_first_linked = models.DateTimeField(
        blank=True,
        null=True,
    )

    date_sensor_modified = models.DateTimeField(
        blank=True,
        null=True,
    )

