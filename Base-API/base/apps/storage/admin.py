from django.contrib import admin

from .models import (CoolingUnit, CoolingUnitCrop, CoolingUnitSpecifications,
                     Crate, Crop, CropType, Location,
                     OperatorAssignedCoolingUnit, Pricing, Produce,
                     SensorIntegration)


# Register your models here.
class CropTypeAdmin(admin.ModelAdmin):
    search_fields = ("name",)


class CropAdmin(admin.ModelAdmin):
    list_display = ("name", "crop_type")
    search_fields = (
        "name",
        "crop_type__name",
    )


class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "point",
        "city",
        "state",
        "street",
        "street_number",
        "zip_code",
    )
    search_fields = (
        "point",
        "city",
        "state",
        "street",
        "street_number",
        "zip_code",
    )


class CoolingUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "metric")
    search_fields = (
        "name",
        "location__name",
    )


class CoolingUnitSpecificationsAdmin(admin.ModelAdmin):
    list_display = ("value", "specification_type", "datetime_stamp")
    search_fields = ("specification_type",)


class ProduceAdmin(admin.ModelAdmin):
    list_display = ("harvest_date", "initial_grade")
    search_fields = (
        "crop__name",
        "crates__cooling_unit__name",
        "harvest_date",
        "initial_grade",
        "id",
    )


class CrateAdmin(admin.ModelAdmin):
    list_display = ("produce", "weight")
    search_fields = (
        "produce__crop__name",
        "weight",
        "price_per_crate_per_pricing_type",
        "cooling_unit__name",
        "id",
    )


class CoolingUnitCropAdmin(admin.ModelAdmin):
    list_display = ("crop", "cooling_unit", "active")
    search_fields = (
        "crop__name",
        "cooling_unit__name",
    )


class PricingAdmin(admin.ModelAdmin):
    list_display = (
        "pricing_type",
        "fixed_rate",
        "daily_rate",
    )
    search_fields = (
        "pricing_type",
        "fixed_rate",
        "daily_rate",
    )


class SensorUserAdmin(admin.ModelAdmin):
    search_fields = (
        "type",
        "username",
        "source_id",
        "cooling_unit__name",
    )
    list_display = (
        "type",
        "username",
        "source_id",
        "cooling_unit",
    )
    exclude = ("password",)


admin.site.register(CropType, CropTypeAdmin)
admin.site.register(Crop, CropAdmin)
admin.site.register(CoolingUnit, CoolingUnitAdmin)
admin.site.register(CoolingUnitSpecifications, CoolingUnitSpecificationsAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Produce, ProduceAdmin)
admin.site.register(Crate, CrateAdmin)
admin.site.register(CoolingUnitCrop, CoolingUnitCropAdmin)
admin.site.register(Pricing, PricingAdmin)
admin.site.register(SensorIntegration, SensorUserAdmin)
admin.site.register(OperatorAssignedCoolingUnit, admin.ModelAdmin)
