from django.core.management.base import BaseCommand
from django.core.management import call_command
from base.apps.prediction.models import StateNg


class Command(BaseCommand):
    help = "Load Nigerian states reference data from fixtures."

    def handle(self, *args, **options):
        """
        Load Nigerian states from fixtures if they don't already exist in the database.
        This ensures the command is idempotent and won't duplicate data on reruns.
        States must be loaded after countries (FK relationship with Country).
        """
        if StateNg.objects.exists():
            state_count = StateNg.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Nigerian states already loaded ({state_count} states exist)")
            )
        else:
            self.stdout.write("Loading Nigerian states fixture...")
            try:
                call_command('loaddata', 'states-ng')
                state_count = StateNg.objects.count()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Successfully loaded {state_count} Nigerian states")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to load Nigerian states fixture: {str(e)}")
                )
                raise
