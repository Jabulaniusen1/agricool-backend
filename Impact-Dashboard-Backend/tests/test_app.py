import unittest

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This method will be run once before any of the tests are executed
        pass

    @classmethod
    def tearDownClass(cls):
        # This method will be run once after all the tests are completed
        pass

    def test_company_slice(self):
        response = client.post(
            "/company-slice/", json={"company_id": 39, "table_name": "company_view"}
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Asserting structure of response
        self.assertIn("report_date", data)
        self.assertIn("company_id", data)

    def test_coolingunit_slice(self):
        response = client.post(
            "/coolingunit-slice/",
            json={
                "unit_ids": [1, 2, 3],
                "start_date": "2021-01-01",
                "end_date": "2021-01-31",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Asserting structure of response. Adjust this according to expected response structure.
        self.assertIn("report_date", data)
        self.assertIn("cooling_unit_id", data)


if __name__ == "__main__":
    unittest.main()
