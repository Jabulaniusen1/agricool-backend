from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.apps.operation.models.checkin import Checkin

from .crop import Crop


class Produce(models.Model):
    crop = models.ForeignKey(
        Crop,
        verbose_name=_("cooling_unit_crop"),
        related_name="produce_cooling_unit_crop",
        on_delete=models.SET_NULL,
        null=True,
    )

    additional_info = models.CharField(_("additional_info"), max_length=255, null=True)

    checkin = models.ForeignKey(
        Checkin,
        verbose_name=_("checkin"),
        related_name="produces",
        on_delete=models.CASCADE,
        null=True,
    )
    harvest_date = models.IntegerField(
        _("harvest_date"),
        null=True,
        blank=True,
    )
    initial_grade = models.IntegerField(
        _("initial_grade"),
        null=True,
        blank=True,
    )
    size = models.IntegerField(
        _("size"),
        null=True,
        blank=True,
    )
    picture = models.FileField(upload_to="produces_picture", null=True, blank=True)

    # Computed fields
    cmp_last_updated_at = models.DateTimeField(_("cmp_last_updated_at"), null=True, blank=True)
    cmp_checkout_completed = models.BooleanField(default=False)

    def compute(self, save=True):
        self.cmp_last_updated_at = timezone.now()
        self.cmp_checkout_completed = self.crates.filter(weight__gt=0).count() == 0

        if save:
            self.save()
