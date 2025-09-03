from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .cooling_unit import CoolingUnit

# Field length constants
PV_PANEL_TYPE_MAX_LENGTH = 255
BATTERY_TYPE_MAX_LENGTH = 255
REFRIGERANT_TYPE_MAX_LENGTH = 32
POWER_SOURCE_MAX_LENGTH = 32
ELECTRIC_STORAGE_SYSTEM_MAX_LENGTH = 32
THERMAL_STORAGE_METHOD_MAX_LENGTH = 32

# Default values
DEFAULT_POWER_CONSUMPTION = 0.0
DEFAULT_DAILY_WATTAGE = 0.0
DEFAULT_PERCENTAGE = 0.0
DEFAULT_COUNT = 0
DEFAULT_SIZE = 0
DEFAULT_WEIGHT = 0.0
DEFAULT_WEIGHT_INT = 0
DEFAULT_FLOAT_VALUE = 0.0
DEFAULT_AMOUNT = 0

# Validator limits
MAX_PERCENTAGE = 100.0


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
        _("power_consumption_in_mt"), null=True, blank=True, default=DEFAULT_POWER_CONSUMPTION
    )

    daily_room_wattage = models.FloatField(
        _("daily_room_wattage"), null=True, blank=True, default=DEFAULT_DAILY_WATTAGE
    )

    power_source_diesel_percent = models.FloatField(
        _("power_source_diesel_percent"),
        null=True,
        blank=True,
        default=DEFAULT_PERCENTAGE,
        validators=[MaxValueValidator(MAX_PERCENTAGE)],
    )

    power_source_grid_percent = models.FloatField(
        _("power_source_grid_percent"),
        null=True,
        blank=True,
        default=DEFAULT_PERCENTAGE,
        validators=[MaxValueValidator(MAX_PERCENTAGE)],
    )

    power_source_pv_percent = models.FloatField(
        _("power_source_pv_percent"),
        null=True,
        blank=True,
        default=DEFAULT_PERCENTAGE,
        validators=[MaxValueValidator(MAX_PERCENTAGE)],
    )

    power_source_biomass_percent = models.FloatField(
        _("power_source_biomass_percent"),
        null=True,
        blank=True,
        default=DEFAULT_PERCENTAGE,
        validators=[MaxValueValidator(MAX_PERCENTAGE)],
    )

    power_source_diesel_consumption_kwh = models.IntegerField(
        _("power_source_diesel_consumption_kwh"), null=True, blank=True, default=DEFAULT_COUNT
    )

    pv_panel_count = models.IntegerField(
        _("pv_panel_count"), null=True, blank=True, default=DEFAULT_COUNT
    )

    pv_panel_size = models.IntegerField(
        _("pv_panel_size"), null=True, blank=True, default=DEFAULT_SIZE
    )

    pv_panel_weight = models.FloatField(
        _("pv_panel_weight"),
        null=True,
        blank=True,
        default=DEFAULT_FLOAT_VALUE,
    )

    pv_panel_max_power = models.FloatField(
        _("pv_panel_max_power"),
        null=True,
        blank=True,
        default=DEFAULT_FLOAT_VALUE,
    )
    pv_panel_type = models.CharField(_("pv_panel_type"), max_length=PV_PANEL_TYPE_MAX_LENGTH, null=True)

    battery_count = models.IntegerField(
        _("battery_count"),
        null=True,
        blank=True,
        default=DEFAULT_COUNT,
    )

    battery_weight = models.IntegerField(
        _("battery_weight"),
        null=True,
        blank=True,
        default=DEFAULT_COUNT,
    )

    battery_capacity = models.FloatField(
        _("battery_capacity"),
        null=True,
        blank=True,
        default=DEFAULT_FLOAT_VALUE,
    )

    battery_max_current = models.FloatField(
        _("battery_max_current"),
        null=True,
        blank=True,
        default=DEFAULT_FLOAT_VALUE,
    )

    battery_type = models.CharField(_("battery_type"), max_length=BATTERY_TYPE_MAX_LENGTH, null=True)

    battery_peak_energy_storage = models.FloatField(
        _("battery_peak_energy_storage"),
        null=True,
        blank=True,
        default=DEFAULT_FLOAT_VALUE,
    )

    refrigerant_type = models.CharField(max_length=REFRIGERANT_TYPE_MAX_LENGTH, choices=RefrigerantType.choices)

    power_source = models.CharField(max_length=POWER_SOURCE_MAX_LENGTH, choices=PowerSource.choices)

    electricity_storage_system = models.CharField(
        max_length=ELECTRIC_STORAGE_SYSTEM_MAX_LENGTH, choices=ElectricStorageSystem.choices
    )

    thermal_storage_method = models.CharField(
        max_length=THERMAL_STORAGE_METHOD_MAX_LENGTH, choices=ThermalStorageMethod.choices
    )

    room_insulator = models.FloatField(
        _("room_insulator"),
        null=True,
        blank=True,
        default=DEFAULT_FLOAT_VALUE,
    )

    amount_refrigerant = models.FloatField(
        _("amount_refrigerant"),
        null=True,
        blank=True,
        default=DEFAULT_COUNT,
    )

    def __str__(self):
        return str(self.cooling_unit)
