from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .cooling_unit import CoolingUnit


class CoolingUnitPower(models.Model):
    class RefrigerantType(models.TextChoices):
        R290 = "r290", "R290"
        R410A = "R-410A", "r-410a"
        R0407c = "R-407c", "r-407c"
        R717 = "R717", "r717"
        R600 = "r600", "R600"
        R600A = "R600A", "r600a"
        R601 = "R601", "r601"
        R601A = "r601a", "R601A"
        OTHER = "other", "Other"

    class PowerSource(models.TextChoices):
        GENERATOR = "generator", "GENERATOR"
        GRID = "grid", "GRID"
        PV_PANELS = "pvpanels", "PVPANELS"
        BIO_MASS = "biomass", "BIOMASS"
        HYBRID = "hybrid", "HYBRID"

    class ElectricStorageSystem(models.TextChoices):
        BATTERY = "battery", "BATTERY"
        THERMAL_STORAGE = "thermal storage", "ice-pack"
        HYBRID = "hybrid", "HYBRID"
        NONE = "none", "NONE"

    class ThermalStorageMethod(models.TextChoices):
        PHASE_CHANGE_MATERIAL = "phase change material"
        ICE_BLOCK_STORAGE = "ice block storage"
        CHILLED_WATER_STORAGE = "chilled water storage"
        OTHER = "other", "OTHER"
        NONE = "none"

    cooling_unit = models.ForeignKey(
        CoolingUnit,
        verbose_name=_("coolingUnit"),
        related_name="cooling_unit_Power",
        on_delete=models.CASCADE,
        null=True,
    )

    power_consumption_in_mt = models.FloatField(
        _("power_consumption_in_mt"), null=True, blank=True, default=0.0
    )

    daily_room_wattage = models.FloatField(
        _("daily_room_wattage"), null=True, blank=True, default=0.0
    )

    power_source_diesel_percent = models.FloatField(
        _("power_source_diesel_percent"),
        null=True,
        blank=True,
        default=0.0,
        validators=[MaxValueValidator(100.0)],
    )

    power_source_grid_percent = models.FloatField(
        _("power_source_grid_percent"),
        null=True,
        blank=True,
        default=0.0,
        validators=[MaxValueValidator(100.0)],
    )

    power_source_pv_percent = models.FloatField(
        _("power_source_pv_percent"),
        null=True,
        blank=True,
        default=0.0,
        validators=[MaxValueValidator(100.0)],
    )

    power_source_biomass_percent = models.FloatField(
        _("power_source_biomass_percent"),
        null=True,
        blank=True,
        default=0.0,
        validators=[MaxValueValidator(100.0)],
    )

    power_source_diesel_consumption_kwh = models.IntegerField(
        _("power_source_diesel_consumption_kwh"), null=True, blank=True, default=0
    )

    pv_panel_count = models.IntegerField(
        _("pv_panel_count"), null=True, blank=True, default=0
    )

    pv_panel_size = models.IntegerField(
        _("pv_panel_size"), null=True, blank=True, default=0
    )

    pv_panel_weight = models.FloatField(
        _("pv_panel_weight"),
        null=True,
        blank=True,
        default=0.0,
    )

    pv_panel_max_power = models.FloatField(
        _("pv_panel_max_power"),
        null=True,
        blank=True,
        default=0.0,
    )
    pv_panel_type = models.CharField(_("pv_panel_type"), max_length=255, null=True)

    battery_count = models.IntegerField(
        _("battery_count"),
        null=True,
        blank=True,
        default=0,
    )

    battery_weight = models.IntegerField(
        _("battery_weight"),
        null=True,
        blank=True,
        default=0,
    )

    battery_capacity = models.FloatField(
        _("battery_capacity"),
        null=True,
        blank=True,
        default=0.0,
    )

    battery_max_current = models.FloatField(
        _("battery_max_current"),
        null=True,
        blank=True,
        default=0.0,
    )

    battery_type = models.CharField(_("battery_type"), max_length=255, null=True)

    battery_peak_energy_storage = models.FloatField(
        _("battery_peak_energy_storage"),
        null=True,
        blank=True,
        default=0.0,
    )

    refrigerant_type = models.CharField(max_length=32, choices=RefrigerantType.choices)

    power_source = models.CharField(max_length=32, choices=PowerSource.choices)

    electricity_storage_system = models.CharField(
        max_length=32, choices=ElectricStorageSystem.choices
    )

    thermal_storage_method = models.CharField(
        max_length=32, choices=ThermalStorageMethod.choices
    )

    room_insulator = models.FloatField(
        _("room_insulator"),
        null=True,
        blank=True,
        default=0.0,
    )

    amount_refrigerant = models.FloatField(
        _("amount_refrigerant"),
        null=True,
        blank=True,
        default=0,
    )

    def __str__(self):
        return {}
