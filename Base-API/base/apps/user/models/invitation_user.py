import os
import base64
# from hashlib import sha256
from phonenumber_field.modelfields import PhoneNumberField
from rest_framework.serializers import ValidationError
# from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import ManyToManyField
from django.utils import timezone
from base.settings import INVITATION_EXPIRY
from .user import User

class InvitationUser(models.Model):
    USER_TYPE_CHOICES = (
        (1, "Service Provider"),
        (2, "Operator"),
        (3, "Farmer"),
    )

    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES)

    phone = PhoneNumberField(
        _("phone"),
    )

    expiration_date = models.DateTimeField()

    code = models.CharField(_("code"), max_length=64)

    sender = models.ForeignKey(
        User,
        verbose_name=_("user"),
        related_name="sent_invitation",
        null=True,
        on_delete=models.SET_NULL,
    )

    cooling_units = ManyToManyField(
        "storage.CoolingUnit",
        verbose_name=_("invitation_cooling_unit"),
        related_name="invitation_cooling_unit",
        blank=True,
    )

    date_invitation_sent = models.DateTimeField(
        blank=True,
        null=True,
    )

    def clean(self):
        if InvitationUser.validate_phone_not_exists(self.phone):
            self.code = InvitationUser.generate_code(self.phone)

    class Meta:
        permissions = (
            ("view_all_invitations", "Can view all invitations"),
            (
                "view_serviceprovider_invitations",
                "Can view service provider invitations",
            ),
            ("view_operator_invitations", "Can view operator invitations"),
            ("add_invitation_serviceprovider", "Can invite a service provider"),
            ("add_invitation_operator", "Can invite an operator"),
        )

    def __str__(self):
        return _("Invite sent to {} to be a service provider").format(self.phone)

    @classmethod
    def validate_phone_not_exists(cls, phone):
        try:
            User.objects.get(phone=phone)
        except User.DoesNotExist:
            return True
        raise ValidationError(
            {"error": _("Phone already assigned. Try a different one")}
        )

    @classmethod
    def generate_code(cls, phone):
        # return sha256(phone.encode() + settings.INVITATION_CODE_SALT.encode()).hexdigest()
        return base64.urlsafe_b64encode(os.urandom(6)).decode()

    @classmethod
    def clear_invitations(cls, **kargs):
        scoped = cls.objects.filter(**kargs)

        count = scoped.count()
        if count > 0:
            scoped.delete()
            return count

        return 0

    @classmethod
    def send_invitation(cls, phone, user, user_type, cooling_units):
        # from base.apps.user.services import send_invitation_phone

        if User.objects.filter(phone=phone).count() > 0:
            raise Exception("User with that phone already exists")

        if cls.objects.filter(phone=phone).count() > 0:
            raise Exception("An invitation for that user already exists")

        invitation = cls.objects.create(
            phone=phone,
            code=InvitationUser.generate_code(phone),
            expiration_date=timezone.now() + INVITATION_EXPIRY,
            sender=user,
            user_type=user_type,
            date_invitation_sent=timezone.now(),
        )
        invitation.cooling_units.set(cooling_units)

        return invitation
