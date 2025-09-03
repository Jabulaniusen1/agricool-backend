from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid

# Field length constants
USERNAME_MAX_LENGTH = 255
FIRST_NAME_MAX_LENGTH = 255
LAST_NAME_MAX_LENGTH = 255
GENDER_MAX_LENGTH = 2
LANGUAGE_MAX_LENGTH = 2
UUID_USERNAME_LENGTH = 30

# Default values
DEFAULT_IS_STAFF = False
DEFAULT_IS_SUPERUSER = False
DEFAULT_IS_EMAIL_PUBLIC = False
DEFAULT_IS_PHONE_PUBLIC = False
DEFAULT_USERNAME = ""

# Error messages
ERROR_EMAIL_REQUIRED = "The given email must be set"
ERROR_SUPERUSER_STAFF = "Superuser must have is_staff=True."
ERROR_SUPERUSER_SUPER = "Superuser must have is_superuser=True."

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError(ERROR_EMAIL_REQUIRED)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", DEFAULT_IS_STAFF)
        extra_fields.setdefault("is_superuser", DEFAULT_IS_SUPERUSER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(ERROR_SUPERUSER_STAFF)
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(ERROR_SUPERUSER_SUPER)

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Language(models.TextChoices):
        ENGLISH = "en"
        HINDI = "hi"
        ORIYA = "or"
        GUJARATI = "gu"
        IGBO = "ig"
        YORUBA = "yo"
        HAUSA = "ha"
        FRENCH = "fr"
        PORTUGESE = "pt"
        ARABIC = "ar"

    username = models.CharField(_("username"), max_length=USERNAME_MAX_LENGTH, unique=True)
    first_name = models.CharField(
        _("first name"),
        max_length=FIRST_NAME_MAX_LENGTH,
    )
    last_name = models.CharField(_("last name"), max_length=LAST_NAME_MAX_LENGTH, blank=True)
    email = models.EmailField(_("email"), blank=True, null=True)
    phone = PhoneNumberField(_("phone"), blank=True, null=True)
    gender = models.CharField(
        _("gender"),
        max_length=GENDER_MAX_LENGTH,
        null=True,
    )

    # Privacy related fields
    is_email_public = models.BooleanField(default=DEFAULT_IS_EMAIL_PUBLIC)
    is_phone_public = models.BooleanField(default=DEFAULT_IS_PHONE_PUBLIC)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()

    class Meta:
        permissions = (
            ("view_all_users", "Can view all users"),
            ("create_user", "Can create a user"),
        )

    last_login = models.DateTimeField(
        blank=True,
        null=True,
    )

    language = models.CharField(
        _("language"),
        max_length=LANGUAGE_MAX_LENGTH,
        choices=Language.choices,
        null=True,
        blank=True,
    )

    def __str__(self):
        return gettext("{}").format(self.first_name)

    def save(self, *args, **kwargs):
        if not self.username or self.username == DEFAULT_USERNAME:
            self.username = uuid.uuid4().hex[:UUID_USERNAME_LENGTH]
        super(User, self).save(*args, **kwargs)
