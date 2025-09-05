
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from base.apps.user.models import Company, ServiceProvider
from base.apps.user.serializers.company import CompanySerializer


class ServiceProviderLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        sp = ServiceProvider.objects.filter(
            Q(user__phone__iexact=attrs[self.username_field])
            | Q(user__email__iexact=attrs[self.username_field])
        ).first()

        if not sp:
            raise serializers.ValidationError({"user": [_("User not exists")]})
        attrs[self.username_field] = sp.user.username
        
        try:
            data = super().validate(attrs)
        except Exception as e:
            raise

        try:
            company = Company.objects.get(id=sp.company.id)
            company_serializer = CompanySerializer(company)
        except Exception as e:
            raise
            
        try:
            if sp.user.language is not self.initial_data["language"]:
                sp.user.language = self.initial_data["language"]
                sp.user.save()
        except KeyError as e:
            pass
        except Exception as e:
            raise
        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Add extra responses here
        data["user"] = {
            "id": sp.user.id,
            "first_name": sp.user.first_name,
            "last_name": sp.user.last_name,
            "email": sp.user.email,
            "gender": sp.user.gender,
            "phone": str(sp.user.phone),
            "last_login": str(sp.user.last_login),
        }
        data["role"] = "Service Provider"
        data["company"] = company_serializer.data
        return data
