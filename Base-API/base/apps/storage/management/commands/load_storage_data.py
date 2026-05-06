from django.core.management.base import BaseCommand
from django.core.management import call_command
from base.apps.storage.models import Crop


class Command(BaseCommand):
    help = "Load crops reference data from fixtures."

    def handle(self, *args, **options):
        """
        Load crops from fixtures if they don't already exist in the database.
        This ensures the command is idempotent and won't duplicate data on reruns.
        """
        if Crop.objects.exists():
            crop_count = Crop.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Crops already loaded ({crop_count} crops exist)")
            )
        else:
            self.stdout.write("Loading crops fixture...")
            try:
                call_command('loaddata', 'crops')
                crop_count = Crop.objects.count()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Successfully loaded {crop_count} crops")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to load crops fixture: {str(e)}")
                )
                raise
