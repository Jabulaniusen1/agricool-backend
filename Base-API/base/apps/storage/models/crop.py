from django.db import models
from django.utils.translation import gettext_lazy as _

from .crop_type import CropType


class Crop(models.Model):
    crop_type = models.ForeignKey(
        CropType,
        verbose_name=_("crop_type"),
        related_name="crop_crop_type",
        on_delete=models.CASCADE,
        default=None,
    )

    name = models.CharField(
        _("name"),
        max_length=255,
    )

    image = models.FileField(upload_to="crop_images", null=True, blank=True)

    optimal_storage_temperature = models.CharField(
        _("optimal_storage_temperature"),
        max_length=255,
        default=None,
        blank=True,
        null=True,
    )

    approximate_shelf_life = models.CharField(
        _("approximate_shelf_life"), max_length=255, null=True, blank=True
    )

    harvested_today = models.PositiveSmallIntegerField(
        _("harvested_today"), default=100, null=True, blank=True
    )

    harvested_yesterday = models.PositiveSmallIntegerField(
        _("harvested_yesterday"), null=True, blank=True
    )

    harvested_day_before_yesterday = models.PositiveSmallIntegerField(
        _("harvested_day_before_yesterday"), null=True, blank=True
    )

    harvested_before = models.PositiveSmallIntegerField(
        _("harvested_before"), null=True, blank=True
    )

    size_selection_1 = models.CharField(
        _("size_selection_1"), max_length=255, null=True, blank=True
    )

    size_selection_2 = models.CharField(
        _("size_selection_2"), max_length=255, null=True, blank=True
    )

    size_selection_3 = models.CharField(
        _("size_selection_3"), max_length=255, null=True, blank=True
    )

    digital_twin_identifier = models.CharField(
        _("dt_identifier"), max_length=255, null=True, blank=True
    )

    dependent_constant = models.FloatField(
        _("dependent_constant"), null=True, blank=True
    )

    activation_energy_constant = models.FloatField(
        _("activation_energy_constant"), null=True, blank=True
    )

    def __str__(self):
        return self.name
