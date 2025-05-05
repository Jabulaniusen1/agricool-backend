from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from django.db.models import ManyToManyField
from base.utils.currencies import validate_currency
from .bank_account import BankAccount

class Company(models.Model):
    name = models.CharField(_("name"), max_length=255, unique=True)

    country = CountryField(_("country"), blank=True, null=True)

    logo = models.FileField(upload_to="company_logos", null=True, blank=True)

    currency = models.CharField(
        _("currency"), max_length=3, default=None, blank=True, null=True,
        validators=[validate_currency]
    )

    digital_twin = models.BooleanField(default=True)

    ML4_market = models.BooleanField(default=False)

    ML4_quality = models.BooleanField(default=False)

    ML4_farmers = models.BooleanField(default=False)

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
        null = True
    )

    # Flags
    flag_opt_out_from_marketplace_filter = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "companies"

    def __str__(self):
        return str(self.name)
