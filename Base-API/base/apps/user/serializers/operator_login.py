from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from base.apps.user.models import Company, Operator
from base.apps.user.serializers.company import CompanySerializer


class OperatorLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        op = Operator.objects.filter(
            user__phone__iexact=attrs[self.username_field]
        ).first()
        if not op:
            print("Operator Login Error", attrs[self.username_field])
            raise serializers.ValidationError({"user": [_("User not exists")]})
        attrs[self.username_field] = op.user.username
        data = super().validate(attrs)
        if op.user.language is not self.initial_data["language"]:
            op.user.language = self.initial_data["language"]
            op.user.save()
        company = Company.objects.get(id=op.company.id)
        company_serializer = CompanySerializer(company)

        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        # Add extra responses here
        data["user"] = {
            "id": op.user.id,
            "first_name": op.user.first_name,
            "last_name": op.user.last_name,
            "gender": op.user.gender,
            "phone": str(op.user.phone),
            "last_login": str(op.user.last_login),
        }
        data["role"] = "Operator"
        data["company"] = company_serializer.data
        return data
