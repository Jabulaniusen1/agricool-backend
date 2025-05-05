from django.db import models
from django.utils.translation import gettext_lazy as _


class CropType(models.Model):
    name = models.CharField(
        _("name"),
        max_length=255,
    )

    def __str__(self):
        return self.name
