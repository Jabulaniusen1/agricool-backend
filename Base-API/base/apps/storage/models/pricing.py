from django.db import models
from django.utils.translation import gettext_lazy as _

# Field length constants
PRICING_TYPE_MAX_LENGTH = 32


class Pricing(models.Model):
    class PricingType(models.TextChoices):
        FIXED = "FIXED", "Fixed"
        PERIODICITY = "PERIODICITY", "Periodicity"

    pricing_type = models.CharField(max_length=PRICING_TYPE_MAX_LENGTH, choices=PricingType.choices)

    fixed_rate = models.FloatField(_("fixed_rate"), blank=True)

    daily_rate = models.FloatField(_("daily_rate"), blank=True)
    
    def save(self, *args, **kwargs):
        """
        Override save to recalculate pricing for all crates using this pricing
        when pricing is updated (as per requirement: existing checked-in crates should update)
        """
        super().save(*args, **kwargs)
        
        # Recalculate pricing for all crates that use this pricing configuration
        from .cooling_unit_crop import CoolingUnitCrop
        from .crate import Crate
        
        # Find all cooling unit crops that use this pricing
        cup_crops = CoolingUnitCrop.objects.filter(pricing=self)
        
        for cup_crop in cup_crops:
            # Get all crates for this cooling unit and crop combination
            crates = Crate.objects.filter(
                cooling_unit=cup_crop.cooling_unit,
                produce__crop=cup_crop.crop,
                weight__gt=0  # Only active crates
            )
            
            # Recalculate pricing for each crate
            for crate in crates:
                crate.compute(save=True)
