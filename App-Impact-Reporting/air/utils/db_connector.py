import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

class DBConnector:
    """Class to connect and run SQL queries to the Database"""
    def __init__(self):
        load_dotenv()
        db_config = dict(
            drivername="postgresql+psycopg2",
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            username=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
        )
        self._setup_connection(db_config)

    def _setup_connection(self, db_config):
        """Create DB engine and setup the connection"""
        password = db_config['password'].replace('\\', '\\\\')

        conn_str = f"{db_config['drivername']}://{db_config['username']}:" \
                   f"{password}@{db_config['host']}:" \
                   f"{db_config['port']}/{db_config['dbname']}"

        self.engine = create_engine(
                            conn_str,
                            paramstyle="format",
                            executemany_mode="values_only",
                            executemany_batch_page_size=200,
                        )

        self.conn = self.engine.connect()

    def get_connection(self):
        return self.conn
