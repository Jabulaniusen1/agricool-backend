import sys
sys.path.append("..")
sys.path.append("../air")

import os
import unittest
from unittest.mock import patch, Mock
from air.utils.db_connector import DBConnector

@patch.dict(os.environ, {"DB_DRIVER": "postgresql+psycopg2"})
@patch.dict(os.environ, {"DB_HOST": "host"})
@patch.dict(os.environ, {"DB_PORT": "10"})
@patch.dict(os.environ, {"DB_NAME": "db"})
@patch.dict(os.environ, {"DB_USERNAME": "uname"})
@patch.dict(os.environ, {"DB_PASSWORD": "pwd"})
class TestDBConnector(unittest.TestCase):

    @patch('air.utils.db_connector.create_engine')
    def test_itialization(self, mock_create_engine):
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_connection = Mock()
        mock_engine.connect.side_effect = [mock_connection]

        db_connector = DBConnector()

        mock_create_engine.assert_called_once_with('postgresql+psycopg2://uname:pwd@host:10/db',
                                                   paramstyle='format',
                                                   executemany_mode='values_only',
                                                   executemany_batch_page_size=200
                                                   )
        mock_engine.connect.assert_called_once()

        self.assertEqual(db_connector.get_connection(), mock_connection, "Connection not saved correctly")

if __name__ == '__main__':
    unittest.main()
