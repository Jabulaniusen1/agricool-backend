from rest_framework.routers import DefaultRouter
from .views import (
    CheckinViewSet,
    CheckoutViewSet,
    MovementViewSet,
    MarketSurveyViewSet,
    CheckoutToCheckinViewSet,
)

router = DefaultRouter()
router.register(r"checkins", CheckinViewSet, basename="checkin")

router.register(r"checkouts", CheckoutViewSet, basename="checkout")

router.register(r"move-checkout", CheckoutToCheckinViewSet, basename="move-checkout")

router.register(r"movements", MovementViewSet, basename="movements")

router.register(r"market-survey", MarketSurveyViewSet, basename="market-survey")

urlpatterns = router.urls
