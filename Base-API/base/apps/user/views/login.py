from rest_framework_simplejwt.views import TokenObtainPairView

from base.apps.user.serializers.farmer_login import FarmerLoginSerializer
from base.apps.user.serializers.operator_login import OperatorLoginSerializer
from base.apps.user.serializers.service_provider_login import (
    ServiceProviderLoginSerializer,
)


class LoginViewSet(TokenObtainPairView):
    serializer_class = FarmerLoginSerializer

    def get_serializer_class(self):
        if "user_type" in self.request.data:
            user_type = self.request.data.get("user_type", None)
            if user_type == "sp":
                return ServiceProviderLoginSerializer
            if user_type == "op":
                return OperatorLoginSerializer
            if user_type == "f":
                return FarmerLoginSerializer
        return None
