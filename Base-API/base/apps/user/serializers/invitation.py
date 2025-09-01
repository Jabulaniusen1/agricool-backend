
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from base.apps.user.models import InvitationUser, User


class InvitationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvitationUser
        fields = ("phone", "code", "user_type", "cooling_units", "expiration_date")
        extra_kwargs = {
            "code": {"read_only": True},
            "expiration_date": {"read_only": True},
        }

    @atomic
    def create(self, validated_data):
        InvitationUser.clear_invitations(phone=validated_data["phone"])

        invite = InvitationUser.send_invitation(
            phone=validated_data["phone"],
            user=self.context["request"].user,
            user_type=validated_data["user_type"],
            cooling_units=validated_data["cooling_units"],
        )

        return invite

    def get_has_accepted(self, instance):
        if User.objects.filter(phone=instance.phone):
            return True

        return False
