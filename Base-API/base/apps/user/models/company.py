from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from django.db.models import ManyToManyField
from base.utils.currencies import validate_currency
from .bank_account import BankAccount

# Field length constants
COMPANY_NAME_MAX_LENGTH = 255
CURRENCY_MAX_LENGTH = 3

# Default values
DEFAULT_DIGITAL_TWIN = True
DEFAULT_ML4_MARKET = False
DEFAULT_ML4_QUALITY = False
DEFAULT_ML4_FARMERS = False
DEFAULT_OPT_OUT_MARKETPLACE = False
DEFAULT_CURRENCY = None

class Company(models.Model):
    name = models.CharField(_("name"), max_length=COMPANY_NAME_MAX_LENGTH, unique=True)

    country = CountryField(_("country"), blank=True, null=True)

    logo = models.FileField(upload_to="company_logos", null=True, blank=True)

    currency = models.CharField(
        _("currency"), max_length=CURRENCY_MAX_LENGTH, default=DEFAULT_CURRENCY, blank=True, null=True,
        validators=[validate_currency]
    )

    digital_twin = models.BooleanField(default=DEFAULT_DIGITAL_TWIN)

    ML4_market = models.BooleanField(default=DEFAULT_ML4_MARKET)

    ML4_quality = models.BooleanField(default=DEFAULT_ML4_QUALITY)

    ML4_farmers = models.BooleanField(default=DEFAULT_ML4_FARMERS)

    crop = ManyToManyField(
        "storage.Crop",
        verbose_name=_("company_crops"),
        related_name="company_crop_shortlist",
        blank=True,
    )

    date_joined = models.DateTimeField(
        blank=True,
        null=True,
    )

    bank_account = models.ForeignKey(
        BankAccount,
        verbose_name=_("bank_account"),
        related_name="company_bank_account",
        on_delete=models.CASCADE,
        null=True
    )

    # Flags
    flag_opt_out_from_marketplace_filter = models.BooleanField(default=DEFAULT_OPT_OUT_MARKETPLACE)

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self):
        return str(self.name)
