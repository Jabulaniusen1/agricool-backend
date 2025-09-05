from rest_framework_simplejwt.views import TokenObtainPairView

from base.apps.user.serializers.farmer_login import FarmerLoginSerializer
from base.apps.user.serializers.operator_login import OperatorLoginSerializer
from base.apps.user.serializers.service_provider_login import (
    ServiceProviderLoginSerializer,
)
from base.utils.recaptcha import validate_recaptcha_field

# User type constants
USER_TYPE_SERVICE_PROVIDER = "sp"
USER_TYPE_OPERATOR = "op"
USER_TYPE_FARMER = "f"

# Request parameter constants
USER_TYPE_PARAM = "user_type"


class LoginViewSet(TokenObtainPairView):
    serializer_class = FarmerLoginSerializer

    def post(self, request, *args, **kwargs):
        print("DEBUG: Login POST request data:", request.data)
        try:
            # Validate reCAPTCHA before processing login
            validate_recaptcha_field(request.data)
            print("DEBUG: reCAPTCHA validation passed")
        except Exception as e:
            print("DEBUG: reCAPTCHA validation failed:", str(e))
            raise
        
        try:
            serializer_class = self.get_serializer_class()
            print("DEBUG: Using serializer class:", serializer_class)
            return super().post(request, *args, **kwargs)
        except Exception as e:
            print("DEBUG: Login error in super().post():", str(e))
            raise

    def get_serializer_class(self):
        print("DEBUG: get_serializer_class - request.data:", self.request.data)
        if USER_TYPE_PARAM in self.request.data:
            user_type = self.request.data.get(USER_TYPE_PARAM, None)
            print("DEBUG: User type from request:", user_type)
            if user_type == USER_TYPE_SERVICE_PROVIDER:
                print("DEBUG: Returning ServiceProviderLoginSerializer")
                return ServiceProviderLoginSerializer
            if user_type == USER_TYPE_OPERATOR:
                print("DEBUG: Returning OperatorLoginSerializer")
                return OperatorLoginSerializer
            if user_type == USER_TYPE_FARMER:
                print("DEBUG: Returning FarmerLoginSerializer")
                return FarmerLoginSerializer
        print("DEBUG: No user_type found, returning None")
        return None
