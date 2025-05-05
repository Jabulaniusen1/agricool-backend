from django.db import models
from django.utils.translation import gettext_lazy as _
from django_cryptography.fields import encrypt

from .cooling_unit import CoolingUnit


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

    type = models.CharField(_("type"), max_length=16, null=False, blank=False, choices=SensorType.choices)

    username = models.CharField(max_length=150, blank=True)
    password = encrypt(models.CharField(max_length=150, default="", blank=True))
    source_id = models.CharField(max_length=64, blank=True)

    date_sensor_first_linked = models.DateTimeField(
        blank=True,
        null=True,
    )

    date_sensor_modified = models.DateTimeField(
        blank=True,
        null=True,
    )

