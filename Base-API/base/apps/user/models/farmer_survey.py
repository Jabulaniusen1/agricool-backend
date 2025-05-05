from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import ManyToManyField
from .farmer import Farmer

class FarmerSurvey(models.Model):
    class UserType(models.TextChoices):
        FARMER = "FARMER", "Farmer"
        TRADER = "TRADER", "Trader"

    farmer = models.ForeignKey(
        Farmer,
        verbose_name=_("farmer"),
        related_name="farmer_farmer_survey",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    user_type = models.CharField(
        max_length=32, choices=UserType.choices, default=None, null=True, blank=True
    )

    experience = models.BooleanField(blank=True, null=True)

    experience_duration = models.PositiveSmallIntegerField(blank=True, null=True)

    date_filled_in = models.DateTimeField(
        blank=True,
        null=True,
    )

    date_last_modified = models.DateTimeField(
        blank=True,
        null=True,
    )
