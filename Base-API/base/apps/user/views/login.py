from rest_framework_simplejwt.views import TokenObtainPairView

from base.apps.user.serializers.farmer_login import FarmerLoginSerializer
from base.apps.user.serializers.operator_login import OperatorLoginSerializer
from base.apps.user.serializers.service_provider_login import (
    ServiceProviderLoginSerializer,
)

# User type constants
USER_TYPE_SERVICE_PROVIDER = "sp"
USER_TYPE_OPERATOR = "op"
USER_TYPE_FARMER = "f"

# Request parameter constants
USER_TYPE_PARAM = "user_type"


class LoginViewSet(TokenObtainPairView):
    serializer_class = FarmerLoginSerializer

    def get_serializer_class(self):
        if USER_TYPE_PARAM in self.request.data:
            user_type = self.request.data.get(USER_TYPE_PARAM, None)
            if user_type == USER_TYPE_SERVICE_PROVIDER:
                return ServiceProviderLoginSerializer
            if user_type == USER_TYPE_OPERATOR:
                return OperatorLoginSerializer
            if user_type == USER_TYPE_FARMER:
                return FarmerLoginSerializer
        return None
