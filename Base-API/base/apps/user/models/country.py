from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from django.db.models import ManyToManyField


class Country(models.Model):
    country = CountryField(_("country"), blank=True, null=True)

    crop = ManyToManyField(
        "storage.Crop",
        verbose_name=_("company_crops"),
        related_name="countryRelated",
        blank=True,
    )

    def __str__(self):
        return "{}".format(
            self.country.name,
        )

    class Meta:
        verbose_name_plural = "countries"
