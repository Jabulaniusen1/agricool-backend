from django.db import models

from base.apps.user.models import User


class OperatorAssignedCoolingUnit(models.Model):
    """
    Information about when each operator was assigned to the Cooling Units.
    """

    operator = models.ForeignKey(
        User,
        related_name="operator_assigned_to_cooling_unit",
        on_delete=models.CASCADE,
    )

    date = models.DateTimeField()
