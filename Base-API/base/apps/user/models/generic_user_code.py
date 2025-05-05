import os
import base64
# from hashlib import sha256
# from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from .user import User


class GenericUserCode(models.Model):
    class Type(models.TextChoices):
        RESET = "RESET", "reset"

    type = models.CharField(max_length=32, choices=Type.choices, default=None, null=True, blank=True)

    user = models.OneToOneField(
        User,
        verbose_name=_("user"),
        related_name="user",
        on_delete=models.CASCADE,
    )

    code = models.CharField(_("code"), max_length=64)

    expiration_date = models.DateTimeField(
        blank=True,
        null=True,
    )

    @classmethod
    def generate_code(cls, phone):
        return base64.urlsafe_b64encode(os.urandom(6)).decode()
        # return sha256(phone.encode() + settings.INVITATION_CODE_SALT.encode()).hexdigest()
