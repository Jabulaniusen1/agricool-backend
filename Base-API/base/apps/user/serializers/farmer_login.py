from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from base.apps.user.models import Farmer

# Token field names
REFRESH_TOKEN_FIELD = "refresh"
ACCESS_TOKEN_FIELD = "access"

# Response field names
USER_FIELD = "user"
PARENT_NAME_FIELD = "parent_name"
ROLE_FIELD = "role"

# Role constants
FARMER_ROLE = "Farmer"

# Error messages
ERROR_USER_NOT_EXISTS = "User not exists"


class FarmerLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        phone_number = attrs[self.username_field]
        f = Farmer.objects.filter(user__phone__iexact=phone_number).first()
        if not f:
            print("Farmer Login Error", attrs[self.username_field])
            raise serializers.ValidationError({"user": [_(ERROR_USER_NOT_EXISTS)]})
        attrs[self.username_field] = f.user.username
        data = super().validate(attrs)

        refresh = self.get_token(self.user)
        data[REFRESH_TOKEN_FIELD] = str(refresh)
        data[ACCESS_TOKEN_FIELD] = str(refresh.access_token)

        # Add extra responses here
        data[USER_FIELD] = {
            "id": f.user.id,
            "first_name": f.user.first_name,
            "last_name": f.user.last_name,
            "gender": f.user.gender,
            "phone": str(f.user.phone),
            "last_login": str(f.user.last_login),
        }
        data[PARENT_NAME_FIELD] = f.parent_name
        data[ROLE_FIELD] = FARMER_ROLE
        return data
