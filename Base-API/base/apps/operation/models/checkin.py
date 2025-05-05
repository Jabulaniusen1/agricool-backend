from django.db import models
from django.utils.translation import gettext_lazy as _
from base.apps.user.models import User, Company
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .movement import Movement

class Checkin(models.Model):
    movement = models.ForeignKey(
        Movement,
        verbose_name=_("movement"),
        related_name="checkins",
        on_delete=models.CASCADE,
    )
    owned_by_user = models.ForeignKey(
        User,
        verbose_name=_("owner"),
        related_name="owned_checkins",
        on_delete=models.CASCADE,
    )
    owned_on_behalf_of_company = models.ForeignKey(
        Company,
        verbose_name=_("owned_on_behalf_of_company"),
        related_name="owned_checkins",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # If we want to delete check-in, we can't leave recompute_digital_twin tasks scheduled and have zombie tasks
    def delete(self, *args, **kwargs):
        periodic_task = None
        try:
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=6,
                period=IntervalSchedule.HOURS,
            )
            periodic_task = PeriodicTask.objects.get(
                interval=schedule,
                name=f"recompute_digital_twin-checkin:{self.id}",
                task="base.apps.storage.tasks.digital_twins.recompute_digital_twin",
            )
        except PeriodicTask.DoesNotExist:
            pass

        if periodic_task:
            periodic_task.enable = False
            periodic_task.save()
            periodic_task.delete()

        super().delete(*args, **kwargs)
