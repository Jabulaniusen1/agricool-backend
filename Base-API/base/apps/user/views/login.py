import logging
from rest_framework_simplejwt.views import TokenObtainPairView

from base.apps.user.serializers.farmer_login import FarmerLoginSerializer
from base.apps.user.serializers.operator_login import OperatorLoginSerializer
from base.apps.user.serializers.service_provider_login import (
    ServiceProviderLoginSerializer,
)
from base.utils.recaptcha import validate_recaptcha_field

logger = logging.getLogger(__name__)

# User type constants
USER_TYPE_SERVICE_PROVIDER = "sp"
USER_TYPE_OPERATOR = "op"
USER_TYPE_FARMER = "f"

# Request parameter constants
USER_TYPE_PARAM = "user_type"


class LoginViewSet(TokenObtainPairView):
    serializer_class = FarmerLoginSerializer

    def post(self, request, *args, **kwargs):
        try:
            # Validate reCAPTCHA before processing login
            validate_recaptcha_field(request.data)
        except Exception as e:
<<<<<<< HEAD
            logger.error(f"reCAPTCHA validation failed: {str(e)}")
=======
            logger.error("reCAPTCHA validation failed")
>>>>>>> development
            raise
        
        try:
            serializer_class = self.get_serializer_class()
<<<<<<< HEAD
            
            if serializer_class is None:
                logger.error("No serializer class found - invalid user_type or missing user_type")
                
            return super().post(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Login processing error: {str(e)}")
=======
            return super().post(request, *args, **kwargs)
        except Exception as e:
            logger.error("Login processing error")
>>>>>>> development
            raise

    def get_serializer_class(self):
        
        if USER_TYPE_PARAM in self.request.data:
            user_type = self.request.data.get(USER_TYPE_PARAM, None)
            if user_type == USER_TYPE_SERVICE_PROVIDER:
                return ServiceProviderLoginSerializer
            if user_type == USER_TYPE_OPERATOR:
                return OperatorLoginSerializer
            if user_type == USER_TYPE_FARMER:
                return FarmerLoginSerializer            
        else:
            logger.warning(f"user_type parameter '{USER_TYPE_PARAM}' not found in request data")
        return None
