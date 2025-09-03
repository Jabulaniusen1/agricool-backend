from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .cooling_unit import CoolingUnit

# Field length constants
SPECIFICATION_TYPE_MAX_LENGTH = 32


class CoolingUnitSpecifications(models.Model):
    class SpecificationType(models.TextChoices):
        TEMPERATURE = "TEMPERATURE", "Temperature"
        HUMIDITY = "HUMIDITY", "Humidity"

    value = models.FloatField(null=False)

    # field used when cooling unit has sensor to save Set_T value retrieved from Ecozen
    set_point_value = models.FloatField(null=True)

    specification_type = models.CharField(
        max_length=SPECIFICATION_TYPE_MAX_LENGTH, choices=SpecificationType.choices
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
        constraints = [
            models.UniqueConstraint(
                fields=["cooling_unit", "datetime_stamp", "specification_type"],
                name="unique_specification_per_cu_timestamp_type"
            )
        ]
