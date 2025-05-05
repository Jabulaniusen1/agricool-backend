from django.db import migrations, models
from django.db.models.deletion import SET_NULL

def populate_owner_user(apps, schema_editor):
    Checkin = apps.get_model('operation', 'checkin')
    for checkin in Checkin.objects.all():
        checkin.owner_user_id = checkin.farmer.user_id  # Assuming farmer has a user_id
        checkin.save()

class Migration(migrations.Migration):

    dependencies = [
        ('operation', '0022_alter_checkout_payment_type'),
    ]

    operations = [
        # Add the owner_user field with null=True to allow temporary null values
        migrations.AddField(
            model_name='checkin',
            name='owner_user',
            field=models.ForeignKey(
                to='user.User',
                verbose_name='owner',
                related_name='owned_checkins',
                on_delete=models.CASCADE,
                null=True,  # Allow null temporarily
                blank=True,
            ),
        ),
        # Add the owner_user field with null=True to allow temporary null values
        migrations.AddField(
            model_name='checkin',
            name='owner_on_behalf_of_company',
            field=models.ForeignKey(
                to='user.company',
                verbose_name='owner_on_behalf_of_company',
                related_name='owned_checkins',
                on_delete=SET_NULL,
                null=True,  # Allow null temporarily
                blank=True,
            ),
        ),

        # Populate owner_user from farmer.user_id
        migrations.RunPython(populate_owner_user),

        # Make owner_user non-nullable
        migrations.AlterField(
            model_name='checkin',
            name='owner_user',
            field=models.ForeignKey(
                to='user.user',
                verbose_name='owner',
                related_name='owned_checkins',
                on_delete=models.CASCADE,
                null=False,  # Now it's non-nullable
            ),
        ),

        # Remove the farmer field
        migrations.RemoveField(
            model_name='checkin',
            name='farmer',
        ),
    ]
