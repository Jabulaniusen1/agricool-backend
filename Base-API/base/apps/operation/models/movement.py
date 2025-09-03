from django.db import models
from django.utils.translation import gettext_lazy as _
from base.apps.user.models import Operator
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from base.utils.currencies import validate_currency
import random, string

class Movement(models.Model):
    class InitiatedFor(models.TextChoices):
        CHECK_IN = "ci", "Check-in"
        CHECK_OUT = "co", "Check-out"
        MARKETPLACE_ORDER = "mo", "Markerplace order"

    initiated_for = models.CharField(max_length=2, choices=InitiatedFor.choices, null=False)
    operator = models.ForeignKey(
        Operator,
        verbose_name=_("operator"),
        related_name="operated_movements",
        on_delete=models.SET_NULL,
        null=True,
    )
    order = models.ForeignKey(
        'marketplace.Order',
        verbose_name=_("order"),
        related_name="movements",
        on_delete=models.SET_NULL,
        null=True,
    )
    date = models.DateTimeField(
        _("date"),
        auto_now=True,
    )
    code = models.CharField(
        _("name"),
        max_length=255,
    )

    # This is used to check in a movement that was tied with a check out
    used_for_checkin = models.BooleanField(default=False)

    @staticmethod
    def generate_code():
        return "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
