import unittest
import configparser
import requests



class FlaskAppTestCase(unittest.TestCase):
    # Base URL for the Dockerized Flask app (change the port if needed)
    BASE_URL = 'http://localhost:8080/prediction' # Modify the port number to the port number used in spawning the
    # Scraping container
    HEADERS = {
        'Content-Type': 'application/json'
    }

    @classmethod
    def setUpClass(cls):
        """Load states and commodities from the config.ini file."""
        config = configparser.RawConfigParser()
        config.optionxform = lambda option: option
        config.read(r'/Users/divinefavourodion/Documents/YourVirtualColdChainAssistant/ML4market-Nigeria/Scraping-module/config.ini')  # Change the path to your config.ini location

        cls.states = dict(config.items('dict_state')).keys()
        cls.commodities = dict(config.items('dict_comm')).keys()

    def test_prediction_endpoint(self):
        """Test the /prediction endpoint with various states and commodities."""
        for state in self.states:
            for commodity in self.commodities:
                payload = {
                    'state': state,
                    'commodity': commodity,
                }
                response = requests.post(self.BASE_URL, json=payload, headers=self.HEADERS)

                self.assertEqual(response.status_code, 200, f"Failed for state: {state}, commodity: {commodity}")
                json_response = response.json()

                self.assertIn('Predictions', json_response,
                              f"Predictions not in response for state: {state}, commodity: {commodity}")
                self.assertIn('Dates', json_response,
                              f"Dates not in response for state: {state}, commodity: {commodity}")

    # Additional tests can be added in the future


if __name__ == '__main__':
    unittest.main()
