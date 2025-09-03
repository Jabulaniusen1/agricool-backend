from logging import getLogger

from django.core.management.base import BaseCommand
from django.db import transaction

from base.apps.security.roles import roles

# Command constants
DRY_RUN_OPTION = "dry_run"
DRY_RUN_HELP = "Runs a dry-run, no data will be altered."
DRY_RUN_DEFAULT = False

# Log message constants
LOG_SUCCESS_MESSAGE = "{count} roles were saved successfully!"
LOG_DRY_RUN_MESSAGE = "Dry run, changes were rolled back."
DRY_RUN_EXCEPTION_MESSAGE = "Dry run, rolling back"


log = getLogger(__name__)


class RollBackException(BaseException):
    pass


class Command(BaseCommand):
    """Loads the groups and permissions defined in roles.py"""

    help = "Load user groups defined in roles.py"

    def add_arguments(self, parser):
        parser.add_argument(
            f"--{DRY_RUN_OPTION}",
            action="store_true",
            default=DRY_RUN_DEFAULT,
            help=DRY_RUN_HELP,
        )

    def handle(self, *args, **options):
        dry_run = options[DRY_RUN_OPTION]
        try:
            with transaction.atomic():
                for role in roles:
                    role.save_permissions()
                if dry_run:
                    raise RollBackException(DRY_RUN_EXCEPTION_MESSAGE)
                log.info(LOG_SUCCESS_MESSAGE.format(count=len(roles)))
        except RollBackException:
            log.info(LOG_DRY_RUN_MESSAGE)
