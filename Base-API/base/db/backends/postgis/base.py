from django.contrib.gis.db.backends.postgis.base import (
    DatabaseWrapper as PostGISDatabaseWrapper,
)

class DatabaseWrapper(PostGISDatabaseWrapper):
    def prepare_database(self):
        # Don't call super().prepare_database() to avoid extension creation
        pass
