from datetime import datetime
from time import strftime
from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "base.apps.user"

    def ready(self):
        """
        Stores as a global variable the last time the backend has been started up.
        Used in the frontend to verify if a logout of the users is needed.
        """
        global APP_LATEST_STARTUP
        APP_LATEST_STARTUP = datetime.now().strftime("%Y%m%d_%H%M")
