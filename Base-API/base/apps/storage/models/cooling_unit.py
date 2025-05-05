from datetime import datetime

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from base.apps.user.models import User

from .location import Location
from .operator_assigned_cooling_unit import OperatorAssignedCoolingUnit


class CoolingUnit(models.Model):
    class CoolingUnitType(models.TextChoices):
        FARM_GATE_STORAGE_ROOM = "FARM_GATE_STORAGE_ROOM", "Farm-gate storage room"
        MARKET_STORAGE_ROOM = "MARKET_STORAGE_ROOM", "Market storage room"
        MOVABLE_UNIT = "MOVABLE_UNIT", "Movable unit"
        OTHER = "OTHER", "Other"

    class CoolingUnitMetric(models.TextChoices):
        CRATES = (
            "CRATES",
            "Crates",
        )
        KILOGRAMS = "KILOGRAMS", "Kilograms"

    operators = models.ManyToManyField(
        User,
        verbose_name=_("operators"),
        related_name="cooling_unit_operators",
        blank=True,
    )
    location = models.ForeignKey(
        Location,
        verbose_name=_("location"),
        related_name="cooling_units",
        on_delete=models.CASCADE,
        default=None,
    )
    name = models.CharField(
        _("name"),
        max_length=255,
    )

    # Maximum volume of food that can be stored, in metric tons (cooling unit capacity)
    food_capacity_in_metric_tons = models.FloatField(
        _("food_capacity_in_metric_tons"), default=None, blank=True, null=True
    )

    room_length = models.FloatField(_("room_length"), null=True, blank=True, default=0)

    room_width = models.FloatField(_("room_width"), null=True, blank=True, default=0)

    room_height = models.FloatField(_("room_height"), null=True, blank=True, default=0)

    room_weight = models.FloatField(_("room_weight"), null=True, blank=True, default=0)

    # Total empty volume of cooling unit, in metric tons (cooling unit size)
    capacity_in_metric_tons = models.FloatField(
        _("capacity_in_metric_tons"), default=None, blank=True, null=True
    )

    capacity_in_number_crates = models.PositiveIntegerField(
        _("capacity_in_number_crates"), default=None, blank=True, null=True
    )
    metric = models.CharField(max_length=32, choices=CoolingUnitMetric.choices)

    sensor = models.BooleanField(default=False)

    cooling_unit_type = models.CharField(
        max_length=32,
        choices=CoolingUnitType.choices,
        default=None,
        null=True,
        blank=True,
    )

    time_pickup_to_customer = models.FloatField(max_length=32, default=2)

    crate_length = models.FloatField(_("crate_length"), default=55.88)

    crate_width = models.FloatField(_("crate_width"), default=40.64)

    crate_height = models.FloatField(_("crate_height"), default=24.13)

    crate_weight = models.FloatField(_("crate_weight"), default=25)

    deleted = models.BooleanField(default=False)

    date_creation = models.DateTimeField(
        blank=True,
        null=True,
    )

    date_last_modified = models.DateTimeField(
        blank=True,
        null=True,
    )

    occupancy_modified_date = models.DateTimeField(
        blank=True,
        null=True,
    )

    occupancy = models.FloatField(
        blank=True,
        null=True,
    )

    date_operator_assigned = models.ManyToManyField(
        OperatorAssignedCoolingUnit,
        related_name="assigned_cooling_unit_operators",
        blank=True,
    )

    public = models.BooleanField(default=False)

    editable_checkins = models.BooleanField(
        default=False
    )

    @transaction.atomic
    def compute(self, save=True):
        from .crate import Crate  # Prevent circular import

        # calculates cooling unit occupancy in percentage
        self.occupancy_modified_date = datetime.now().astimezone()

        full_capacity = (
            self.capacity_in_number_crates
            if (
                    self.capacity_in_number_crates
                    and self.metric == "CRATES"
            )
            else (
                self.food_capacity_in_metric_tons
                if self.food_capacity_in_metric_tons
                else self.capacity_in_metric_tons
            )
        )

        cubic_meter_crate = (self.crate_length * self.crate_width * self.crate_height) / 1000000
        cu_crates = Crate.objects.filter(cooling_unit__id=self.id, weight__gt=0).count()

        # the magic number of 0.68 is provided by BASE/EMPA as an estimation of how much of the room is used for storage
        dividor = (
            cu_crates
            if (
                    self.capacity_in_number_crates
                    and self.metric == "CRATES"
            )
            else cu_crates * cubic_meter_crate * 0.68
        )
        self.occupancy = dividor / full_capacity
        self.save()

    def __str__(self):
        return self.name
