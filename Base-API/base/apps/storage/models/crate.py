from django.db import models, transaction
from django.db.models import OuterRef
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.apps.operation.services.checkout import (
    get_total_in_cooling_fees, get_total_paid_in_cooling_fees)
from base.utils.currencies import validate_currency

from .cooling_unit import CoolingUnit
from .produce import Produce


class Crate(models.Model):
    produce = models.ForeignKey(Produce, verbose_name=_("produce"), related_name="crates", on_delete=models.SET_NULL, null=True)
    cooling_unit = models.ForeignKey(CoolingUnit,verbose_name=_("cooling_unit"),related_name="crate_cooling_unit",on_delete=models.SET_NULL,null=True)
    initial_weight = models.FloatField(_("initial_weight"), default=None)
    weight = models.FloatField(_("weight"), default=None)
    remaining_shelf_life = models.IntegerField(_("remaining_shelf_life"),default=None,blank=True,null=True)
    tag = models.CharField(_("tag"), max_length=255, null=True)

    # Digital Twin related
    runDT = models.BooleanField(blank=True, null=True, default=False)
    quality_dt = models.FloatField(_("quality_computed_dt"), default=-1)
    temperature_dt = models.FloatField(_("temperature_computed_dt"), default=290.4)
    modified_dt = models.DateTimeField(
        blank=True,
        null=True,
    )

    # Forecasting related
    planned_days = models.PositiveIntegerField(
        _("planned_days"), default=None, null=True, blank=True
    )

    # Pricing related
    currency = models.CharField(_("currency"), max_length=3, default=None, blank=True, null=True, validators=[validate_currency])
    price_per_crate_per_pricing_type = models.FloatField(_("price_per_crate_per_pricing_type"), default=0)

    # Computed fields
    cmp_last_updated_at = models.DateTimeField(_("cmp_last_updated_at"), null=True, blank=True)
    cmp_fully_checked_out = models.BooleanField(default=False) # should be marked when the crate is fully checked out
    cmp_total_in_cooling_fees = models.FloatField(default=0)
    cmp_total_paid_in_cooling_fees = models.FloatField(default=0)
    cmp_total_due_in_cooling_fees = models.FloatField(default=0)

    @transaction.atomic
    def compute(self, save=False, compute_dependencies=True):
        self.cmp_last_updated_at = timezone.now()
        self.cmp_fully_checked_out = self.weight <= 0

        self.cmp_total_in_cooling_fees = get_total_in_cooling_fees(self)
        self.cmp_total_paid_in_cooling_fees = get_total_paid_in_cooling_fees(self)
        self.cmp_total_due_in_cooling_fees = self.cmp_total_in_cooling_fees - self.cmp_total_paid_in_cooling_fees

        if save:
            self.save()

        if compute_dependencies:
            # Recompute the produce
            self.produce.compute(save=save)

    @staticmethod
    def generate_checkedin_crates_subquery(pk="id"):
        return Crate.objects.filter(
            produce=OuterRef(pk),  # Reference to the current Produce instance
            weight__gt=0
        )

    def __str__(self):
        return "{}: {}".format(self.remaining_shelf_life, self.weight)
