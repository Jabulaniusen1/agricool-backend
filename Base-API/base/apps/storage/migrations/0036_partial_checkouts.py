from django.db import migrations, models
from django.utils import timezone

def migrate_fully_checked_out(apps, schema_editor):
    # Get the models for Crate and CheckoutCrateDetails
    Crate = apps.get_model('storage', 'Crate')
    CratePartialCheckout = apps.get_model('storage', 'CratePartialCheckout')

    # Loop through all crates that have a checkout set (i.e. check_out is not null)
    for crate in Crate.objects.filter(check_out__isnull=False).iterator():
        # TODO: Calculate cooling_fees

        # Create a CheckoutCrateDetails entry for each crate
        CratePartialCheckout.objects.create(
            checkout=crate.check_out,
            crate=crate,
            percentage=1.0,  # Since the entire crate was checked out, set to 100%
            weight_in_kg=crate.weight,
            cooling_fees=0,
        )

    # Loop through all crates that have a checkout set (i.e. check_out is not null)
    Crate.objects.filter(check_out__isnull=False).update(
        fully_checked_out=True,
        weight=0.0,
    )


def reverse_migrate_fully_checked_out(apps, schema_editor):
    # In case of rollback, we simply won't do anything, as we removed the `check_out` field from Crate
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('operation', '0025_integration_with_movement'),
        ('storage', '0035_alter_currency_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='CratePartialCheckout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percentage', models.FloatField(default=0, verbose_name='percentage')),
                ('weight_in_kg', models.PositiveIntegerField(default=0, verbose_name='weight_in_kg')),
                ('cooling_fees', models.PositiveIntegerField(default=0, verbose_name='cooling_fees')),
                ('checkout', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='partial_checkouts', to='operation.checkout', verbose_name='checkout')),
                ('crate', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='partial_checkouts', to='storage.crate', verbose_name='crate')),
            ],
        ),
        migrations.AddConstraint(
            model_name='cratepartialcheckout',
            constraint=models.CheckConstraint(check=models.Q(('percentage__gte', 0), ('percentage__lte', 1)), name='checkout_crate_percentage_check'),
        ),
        migrations.AlterUniqueTogether(
            name='cratepartialcheckout',
            unique_together={('checkout', 'crate')},
        ),

        migrations.AddField(
            model_name='crate',
            name='fully_checked_out',
            field=models.BooleanField(default=False),
        ),

        # Data migration to transfer `check_out` field data to CheckoutCrateDetails
        migrations.RunPython(migrate_fully_checked_out, reverse_migrate_fully_checked_out),

        # Remove the `check_out` field from Crate
        migrations.RemoveField(
            model_name='crate',
            name='check_out',
        ),

        migrations.RenameField(
            model_name='produce',
            old_name='checkout_complete',
            new_name='cmp_checkout_completed',
        ),
        migrations.AddField(
            model_name='produce',
            name='cmp_last_updated_at',
            field=models.DateTimeField(default=timezone.now, verbose_name='cmp_last_updated_at'),
        ),

        migrations.AlterField(
            model_name='crate',
            name='produce',
            field=models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, related_name='crates', to='storage.produce', verbose_name='produce'),
        ),
    ]
