from django.db import models
from django.utils.translation import gettext_lazy as _

# Field length constants
CROP_TYPE_NAME_MAX_LENGTH = 255


class CropType(models.Model):
    name = models.CharField(
        _("name"),
        max_length=CROP_TYPE_NAME_MAX_LENGTH,
    )

    def __str__(self):
        return self.name
