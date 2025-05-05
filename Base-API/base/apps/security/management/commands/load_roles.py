from logging import getLogger

from django.core.management.base import BaseCommand
from django.db import transaction

from base.apps.security.roles import roles


log = getLogger(__name__)


class RollBackException(BaseException):
    pass


class Command(BaseCommand):
    """Loads the groups and permissions defined in roles.py"""

    help = "Load user groups defined in roles.py"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry_run",
            action="store_true",
            default=False,
            help="Runs a dry-run, no data will be altered.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        try:
            with transaction.atomic():
                for role in roles:
                    role.save_permissions()
                if dry_run:
                    raise RollBackException("Dry run, rolling back")
                log.info(f"{len(roles)} roles were saved successfully!")
        except RollBackException:
            log.info("Dry run, changes were rolled back.")
