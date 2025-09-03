# Generated manually to update existing PAYTACK data to PAYSTACK

from django.db import migrations


def update_paystack_values(apps, schema_editor):
    """Update existing PAYTACK values to PAYSTACK"""
    Checkout = apps.get_model('operation', 'Checkout')
    updated_count = Checkout.objects.filter(payment_gateway='PAYTACK').update(payment_gateway='PAYSTACK')
    if updated_count > 0:
        print(f"Updated {updated_count} checkout records from PAYTACK to PAYSTACK")


def reverse_paystack_values(apps, schema_editor):
    """Reverse: Update PAYSTACK back to PAYTACK if needed"""
    Checkout = apps.get_model('operation', 'Checkout')
    updated_count = Checkout.objects.filter(payment_gateway='PAYSTACK').update(payment_gateway='PAYTACK')
    if updated_count > 0:
        print(f"Reverted {updated_count} checkout records from PAYSTACK to PAYTACK")


class Migration(migrations.Migration):

    dependencies = [
        ('operation', '0031_alter_checkout_payment_gateway'),
    ]

    operations = [
        migrations.RunPython(update_paystack_values, reverse_paystack_values),
    ]