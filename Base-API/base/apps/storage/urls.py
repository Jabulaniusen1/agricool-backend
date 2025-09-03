from rest_framework.routers import DefaultRouter

from .views import (
    ComsolCallbackViewSet,
    CoolingUnitCapacityViewSet,
    CoolingUnitCropViewSet,
    CoolingUnitProduceViewSet,
    CoolingUnitSpecificationsViewSet,
    CoolingUnitTemperatureViewSet,
    CoolingUnitViewSet,
    CrateViewSet,
    CropTypeViewSet,
    CropViewSet,
    EcozenViewSet,
    FarmerCoolingUnitProduceViewSet,
    LocationViewSet,
    MobileAppMinimumVersionCodesViewSet,
    NextCheckoutViewSet,
    ProduceViewSet,
    SensorIntegrationViewSet,
)

router = DefaultRouter()
router.register(r"(?P<version>(v1))/crop-types", CropTypeViewSet, basename="crop")
router.register(r"(?P<version>(v1))/crops", CropViewSet, basename="produce")
router.register(
    r"(?P<version>(v1))/cooling-units", CoolingUnitViewSet, basename="cooling-unit"
)
router.register(r"(?P<version>(v1))/crates", CrateViewSet, basename="crate")
router.register(r"(?P<version>(v1))/locations", LocationViewSet, basename="location")
router.register(r"(?P<version>(v1))/produces", ProduceViewSet, basename="produces")
router.register(
    r"(?P<version>(v1))/cooling-unit-crops",
    CoolingUnitCropViewSet,
    basename="cooling-unit-crop",
)
router.register(
    r"(?P<version>(v1))/next-checkouts", NextCheckoutViewSet, basename="next-checkouts"
)

router.register(
    r"(?P<version>(v1))/cooling-unit-capacity",
    CoolingUnitCapacityViewSet,
    basename="cooling-unit-capacity",
)

router.register(
    r"(?P<version>(v1))/cooling-unit-specifications",
    CoolingUnitSpecificationsViewSet,
    basename="cooling-unit-specifications",
)

router.register(
    r"(?P<version>(v1))/cooling-unit-temperatures",
    CoolingUnitTemperatureViewSet,
    basename="cooling-unit-temperatures",
)

router.register(r"(?P<version>(v1))/ecozen", EcozenViewSet, basename="ecozen")
router.register(
    r"(?P<version>(v1))/user-sensor", SensorIntegrationViewSet, basename="user-sensor"
)

router.register(
    r"version-code",
    MobileAppMinimumVersionCodesViewSet,
    basename="minimum-client-version-codes",
)

router.register(
    r"(?P<version>(v1))/comsol", ComsolCallbackViewSet, basename="comsol-callback"
)

router.register(
    r"(?P<version>(v1))/cooling-units/(?P<cooling_unit_id>\d+)/produces",
    CoolingUnitProduceViewSet,
    basename="cooling-unit-produces"
)

router.register(
    r"(?P<version>(v1))/cooling-units/(?P<cooling_unit_id>\d+)/farmers/(?P<farmer_id>\d+)/produces",
    FarmerCoolingUnitProduceViewSet,
    basename="farmer-cooling-unit-produces"
)

urlpatterns = router.urls
