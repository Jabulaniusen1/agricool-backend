from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from base.apps.user.models import Farmer


class FarmerLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        phone_number = attrs[self.username_field]
        f = Farmer.objects.filter(user__phone__iexact=phone_number).first()
        if not f:
            print("Farmer Login Error", attrs[self.username_field])
            raise serializers.ValidationError({"user": [_("User not exists")]})
        attrs[self.username_field] = f.user.username
        data = super().validate(attrs)

        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Add extra responses here
        data["user"] = {
            "id": f.user.id,
            "first_name": f.user.first_name,
            "last_name": f.user.last_name,
            "gender": f.user.gender,
            "phone": str(f.user.phone),
            "last_login": str(f.user.last_login),
        }
        data["parent_name"] = f.parent_name
        data["role"] = "Farmer"
        return data
