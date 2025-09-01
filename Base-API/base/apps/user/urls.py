from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt import views as jwt_views

from base.settings import ENVIRONMENT

from .views import (
    CompanyViewSet,
    FarmerSurveyViewSet,
    FarmerViewSet,
    GenericCodeViewSet,
    InviteOperatorViewSet,
    InviteServiceProviderViewSet,
    LoginViewSet,
    NotificationViewSet,
    OperatorRegistrationWithInvitationViewSet,
    OperatorViewSet,
    ResetPasswordViewSet,
    ServiceProviderRegistrationViewSet,
    ServiceProviderRegistrationWithInvitationViewSet,
    ServiceProviderViewSet,
    UserViewSet,
)

router = DefaultRouter()

router.register(r"(?P<version>(v1))/users", UserViewSet, basename="user")
router.register(r"(?P<version>(v1))/companies", CompanyViewSet, basename="company")
router.register(
    r"(?P<version>(v1))/service-providers",
    ServiceProviderViewSet,
    basename="service_provider",
)
router.register(r"(?P<version>(v1))/farmers", FarmerViewSet, basename="farmers")
router.register(r"(?P<version>(v1))/operators", OperatorViewSet, basename="operators")
router.register(
    r"(?P<version>(v1))/service-provider-invite",
    InviteServiceProviderViewSet,
    basename="service-provider-invite",
)
router.register(
    r"(?P<version>(v1))/operator-invite",
    InviteOperatorViewSet,
    basename="operator-invite",
)
router.register(
    r"(?P<version>(v1))/service-provider-signup",
    ServiceProviderRegistrationViewSet,
    basename="service-provider-signup",
)
router.register(
    r"(?P<version>(v1))/service-provider-invite-signup",
    ServiceProviderRegistrationWithInvitationViewSet,
    basename="service-provider-invite-signup",
)

router.register(
    r"(?P<version>(v1))/operator-invite-signup",
    OperatorRegistrationWithInvitationViewSet,
    basename="operator-invite-signup",
)

router.register(
    r"(?P<version>(v1))/farmer-survey", FarmerSurveyViewSet, basename="farmer-survey"
)

router.register(
    r"(?P<version>(v1))/notification", NotificationViewSet, basename="notification"
)

router.register(
    r"(?P<version>(v1))/reset-password", ResetPasswordViewSet, basename="reset-password"
)

router.register(r"(?P<version>(v1))/code", GenericCodeViewSet, basename="code")

# Development test endpoints
if ENVIRONMENT == "development" or ENVIRONMENT == "e2e":
    from base.apps.user.views import DevelopmentViewSet

    router.register(r"development", DevelopmentViewSet, basename="development")

urlpatterns = router.urls + [
    path("token/obtain/", jwt_views.TokenObtainPairView.as_view(), name="token_create"),
    path("token/refresh/", jwt_views.TokenRefreshView.as_view(), name="token_refresh"),
    path("v1/login/", LoginViewSet.as_view(), name="login"),
]
