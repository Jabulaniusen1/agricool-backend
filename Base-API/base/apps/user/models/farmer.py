from django.db import models
from django.utils.translation import gettext_lazy as _

from .company import Company
from .operator import Operator
from .user import User


class Farmer(models.Model):
    birthday = models.DateTimeField(blank=True, null=True)
    user = models.OneToOneField(
        User,
        verbose_name=_("user"),
        related_name="farmer",
        on_delete=models.CASCADE,
    )
    parent_name = models.CharField(_("parent_name"), max_length=255, blank=True)

    created_by = models.ForeignKey(
        Operator,
        verbose_name=_("created_by"),
        related_name="created_by",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    isUnknown = models.BooleanField(default=False)

    smartphone = models.BooleanField(default=False)

    country = models.CharField(max_length=150, null=True, blank=True)

    user_code = models.CharField(max_length=8, unique=True, blank=True, null=True)

    companies = models.ManyToManyField(
        Company,
        verbose_name=_("worked_with_company"),
        related_name="worked_with_company",
        blank=True,
    )

    cooling_units = models.ManyToManyField(
        "storage.CoolingUnit",
        verbose_name=_("cooling_unit_used"),
        related_name="cooling_unit_used",
        blank=True,
    )

    def __str__(self):
        return gettext("{}").format(self.user)
