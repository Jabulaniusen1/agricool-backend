import unittest

import pandas as pd
from dotenv import load_dotenv

from DataSlicer import CompanySlicer, CoolingUnitSlicer


class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_params = cls.get_db_params()

    @staticmethod
    def get_db_params() -> dict:
        load_dotenv()

        # Get database configurations from environment variables
        params = {
            "host": "***REMOVED***",
            "dbname": "postgres",
            "user": "coldtivatedbuser",
            "password": "***REMOVED***",
            "port": "5432",
        }
        return params


class TestCompanyDataSlicer(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slicer = CompanySlicer(cls.db_params)

    @classmethod
    def tearDownClass(cls):
        cls.slicer.close()

    def test_get_data_by_company_id(self):
        company_id = 39
        table_name = "company_view"
        df_slice = self.slicer.slice_table(company_id, table_name)

        # Assert that the returned dataframe is not empty
        self.assertFalse(df_slice.empty)

        # Assert that the company_id in the returned dataframe matches the requested one
        self.assertEqual(df_slice["company_id"].iloc[0], company_id)


class TestCoolingUnitDataSlicer(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slicer = CoolingUnitSlicer(cls.db_params)

    @classmethod
    def tearDownClass(cls):
        cls.slicer.close()

    def test_get_data_by_unit_ids(self):
        unit_ids = [1, 2, 3]
        date_range = pd.date_range("2023-08-01", "2023-08-31")
        df_slice = self.slicer.slice_table(unit_ids, date_range)

        # Assert that the returned dataframe is not empty
        self.assertFalse(df_slice.empty)

        # Assert that the unit_ids in the returned dataframe are all in the requested list
        self.assertTrue(all(id in unit_ids for id in df_slice["unit_id"].unique()))


if __name__ == "__main__":
    unittest.main()
