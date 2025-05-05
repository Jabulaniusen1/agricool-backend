
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone

# There were some checkouts in the database that had the wrong datapoints in the computed fields.
# This migration recomputes the computed amounts for all the checkouts.
#
# We can test if the migration fixed the issue by running the following query:
#
# SELECT
#     id,
#     cmp_total_cooling_fees_amount AS subtotal,
#     discount_amount AS discount,
#     cmp_total_amount AS total,
#     (cmp_total_cooling_fees_amount - discount_amount) AS computed_total,
#     (cmp_total_amount <> (cmp_total_cooling_fees_amount - discount_amount)) AS total_mismatch
# FROM operation_checkout;
#

def compute_checkouts(apps, schema_editor):
    Checkout = apps.get_model('operation', 'Checkout')
    CratePartialCheckout = apps.get_model('storage', 'CratePartialCheckout')

    # Per each checkout, call the Checkout.compute method
    for checkout in Checkout.objects.all().iterator():
        checkout.cmp_last_updated_at = timezone.now()
        checkout.cmp_total_cooling_fees_amount = (
            CratePartialCheckout.objects.filter(checkout=checkout).aggregate(
                total_paid_in_cooling_fees=models.Sum('cooling_fees')
            )['total_paid_in_cooling_fees']
        ) or 0

        checkout.cmp_total_amount = checkout.cmp_total_cooling_fees_amount - (checkout.discount_amount or 0)
        checkout.save()


class Migration(migrations.Migration):

    dependencies = [
        ('operation', '0029_fix_movement_initiated_by'),
        ('storage', '0042_recompute_initial_weight'),
    ]


    operations = [
        migrations.RunPython(compute_checkouts),
    ]
