from django.apps import AppConfig


class StorageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "base.apps.storage"

    def ready(self):
        """
        Stores as a global variable the last version code.
        Need to be updated only if we deploy some changes that impact the frontend
        Used in the frontend to verify if the version code is the good one and display
        a popup to download new version in case it is needed.
        """
        global ANDROID_VERSION_CODE
        global IOS_VERSION_CODE

        ANDROID_VERSION_CODE = 70354
        IOS_VERSION_CODE = 70354
