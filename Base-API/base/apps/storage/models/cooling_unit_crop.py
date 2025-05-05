from django.db import models
from django.utils.translation import gettext_lazy as _

from .cooling_unit import CoolingUnit
from .crop import Crop
from .pricing import Pricing


class CoolingUnitCrop(models.Model):
    crop = models.ForeignKey(
        Crop,
        verbose_name=_("crop"),
        related_name="cooling_unit_crop_crop",
        on_delete=models.SET_NULL,
        null=True,
    )

    cooling_unit = models.ForeignKey(
        CoolingUnit,
        verbose_name=_("cooling_unit"),
        related_name="crop_cooling_unit",
        on_delete=models.SET_NULL,
        null=True,
    )

    pricing = models.ForeignKey(
        Pricing,
        verbose_name=_("cooling_unit_crop-pricing"),
        related_name="crop_pricing",
        on_delete=models.SET_NULL,
        null=True,
    )

    # When add an available crop to the cooling unit, pass the field to True
    active = models.BooleanField(default=False)

    def __str__(self):
        return "{} : {}".format(self.crop, self.cooling_unit)
