from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .cooling_unit import CoolingUnit


class CoolingUnitSpecifications(models.Model):
    class SpecificationType(models.TextChoices):
        TEMPERATURE = "TEMPERATURE", "Temperature"
        HUMIDITY = "HUMIDITY", "Humidity"

    value = models.FloatField(null=False)

    # field used when cooling unit has sensor to save Set_T value retrieved from Ecozen
    set_point_value = models.FloatField(max_length=32, null=True)

    specification_type = models.CharField(
        max_length=32, choices=SpecificationType.choices
    )

    datetime_stamp = models.DateTimeField(default=timezone.now)

    cooling_unit = models.ForeignKey(
        CoolingUnit,
        verbose_name=_("cooling_unit"),
        related_name="specification_cooling_unit",
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        verbose_name_plural = "cooling unit specifications"
