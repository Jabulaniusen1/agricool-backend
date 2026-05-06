from django.core.management.base import BaseCommand
from django.core.management import call_command
from base.apps.user.models import Country


class Command(BaseCommand):
    help = "Load countries reference data from fixtures."

    def handle(self, *args, **options):
        """
        Load countries from fixtures if they don't already exist in the database.
        This ensures the command is idempotent and won't duplicate data on reruns.
        Countries must be loaded after crops (M2M relationship with Crop).
        """
        if Country.objects.exists():
            country_count = Country.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Countries already loaded ({country_count} countries exist)")
            )
        else:
            self.stdout.write("Loading countries fixture...")
            try:
                call_command('loaddata', 'countries')
                country_count = Country.objects.count()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Successfully loaded {country_count} countries")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to load countries fixture: {str(e)}")
                )
                raise
