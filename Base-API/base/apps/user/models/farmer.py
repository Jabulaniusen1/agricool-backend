from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from .company import Company
from .operator import Operator
from .user import User

# Field length constants
PARENT_NAME_MAX_LENGTH = 255
COUNTRY_MAX_LENGTH = 150
USER_CODE_MAX_LENGTH = 8

# Default values
DEFAULT_IS_UNKNOWN = False
DEFAULT_SMARTPHONE = False


class Farmer(models.Model):
    birthday = models.DateTimeField(blank=True, null=True)
    user = models.OneToOneField(
        User,
        verbose_name=_("user"),
        related_name="farmer",
        on_delete=models.CASCADE,
    )
    parent_name = models.CharField(_("parent_name"), max_length=PARENT_NAME_MAX_LENGTH, blank=True)

    created_by = models.ForeignKey(
        Operator,
        verbose_name=_("created_by"),
        related_name="created_by",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    is_unknown = models.BooleanField(default=DEFAULT_IS_UNKNOWN)

    smartphone = models.BooleanField(default=DEFAULT_SMARTPHONE)

    country = models.CharField(max_length=COUNTRY_MAX_LENGTH, null=True, blank=True)

    user_code = models.CharField(max_length=USER_CODE_MAX_LENGTH, unique=True, blank=True, null=True)

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
