import unittest
import json
from unittest.mock import patch, MagicMock

# Assuming main.py (which creates Flask app `app`) is in the parent directory.
# Requires PYTHONPATH to include the project root, or for tests to be run in a way that main.py is discoverable.
from main import app

# Sample data that scraper or calculator might return, used for mocking
MOCK_SCRAPE_RESULT_SUCCESS = {
    "listing_url": "https://www.airbnb.com/rooms/mock123",
    "listing_id": "mock123",
    "title": "Mocked Test Property",
    "price_per_night": 120.0,
    "num_bedrooms": 2,
    "num_bathrooms": 1.0,
    "num_reviews": 75,
    "average_rating": 4.5,
    "cleaning_fee": 50.0,
    "address_neighborhood": "Mockville, MC"
}

MOCK_SCRAPE_RESULT_ERROR = {"error": "Could not fetch URL", "listing_url": "https://www.airbnb.com/rooms/fail"}

MOCK_COMPARABLES_RESULT = [
    {
        "listing_url": "https://www.airbnb.com/rooms/comp1", "title": "Comp 1",
        "price_per_night": 110.0, "num_bedrooms": 2, "num_reviews": 50
    }
]

MOCK_CALCULATOR_RESULT = {
    "investment_summary": {"total_investment": 100000, "monthly_mortgage_payment": 500},
    "revenue_scenarios": {"average_case": {"annual_revenue": 25000}},
    # ... other calculator output fields
}

class TestAPI(unittest.TestCase):

    def setUp(self):
        app.testing = True # Critical: sets up the application for testing
        self.app = app.test_client()

    def test_home_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["message"], "Welcome to the Airbnb Underwriting API")

    def test_health_route_main(self): # Renamed to avoid conflict
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["status"], "healthy")

    def test_underwriting_health_route(self):
        response = self.app.get('/api/underwriting/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["status"], "healthy")
        self.assertIn("airbnb-underwriter", data["service"])

    def test_documentation_route(self):
        response = self.app.get('/api/underwriting/documentation')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn("endpoints", data)

    @patch('underwriting.scrape_airbnb_listing') # Patch where it's used in underwriting.py
    def test_test_scraper_success_query_param(self, mock_scrape_airbnb_listing):
        mock_scrape_airbnb_listing.return_value = MOCK_SCRAPE_RESULT_SUCCESS

        response = self.app.get('/api/underwriting/test-scraper?airbnb_url=some_url')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        mock_scrape_airbnb_listing.assert_called_once_with('some_url', allow_mock=False)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scrape_results"], MOCK_SCRAPE_RESULT_SUCCESS)

    @patch('underwriting.scrape_airbnb_listing')
    def test_test_scraper_success_json_body(self, mock_scrape_airbnb_listing):
        mock_scrape_airbnb_listing.return_value = MOCK_SCRAPE_RESULT_SUCCESS

        response = self.app.post('/api/underwriting/test-scraper', json={'airbnb_url': 'some_url_post'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        mock_scrape_airbnb_listing.assert_called_once_with('some_url_post', allow_mock=False)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["scrape_results"], MOCK_SCRAPE_RESULT_SUCCESS)

    def test_test_scraper_missing_url_get(self):
        response = self.app.get('/api/underwriting/test-scraper')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn("error", data)
        self.assertEqual(data["error"], "airbnb_url is required in query parameters (GET) or JSON/form body (POST)")

    def test_test_scraper_missing_url_post(self):
        response = self.app.post('/api/underwriting/test-scraper', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn("error", data)
        self.assertEqual(data["error"], "airbnb_url is required in query parameters (GET) or JSON/form body (POST)")

    @patch('underwriting.scrape_airbnb_listing')
    def test_test_scraper_scraper_returns_error(self, mock_scrape_airbnb_listing):
        mock_scrape_airbnb_listing.return_value = MOCK_SCRAPE_RESULT_ERROR

        response = self.app.get('/api/underwriting/test-scraper?airbnb_url=fail_url')
        # The error in MOCK_SCRAPE_RESULT_ERROR is "Could not fetch URL"
        # This should result in a 502 from the API if "fetching" or "parsing" is in the error message
        self.assertEqual(response.status_code, 502)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn("error", data)
        self.assertTrue(MOCK_SCRAPE_RESULT_ERROR["error"] in data["error"])


    @patch('underwriting.calculate_underwriting')
    @patch('underwriting.AirbnbScraper') # Patch the class
    @patch('underwriting.scrape_airbnb_listing')
    def test_analyze_property_success(self, mock_scrape_listing, MockAirbnbScraperClass, mock_calculate_underwriting):
        # Setup mocks
        mock_scrape_listing.return_value = MOCK_SCRAPE_RESULT_SUCCESS

        mock_scraper_instance = MockAirbnbScraperClass.return_value # Get the instance
        mock_scraper_instance.find_comparable_listings.return_value = MOCK_COMPARABLES_RESULT

        mock_calculate_underwriting.return_value = MOCK_CALCULATOR_RESULT

        payload = {
            'airbnb_url': 'https://www.airbnb.com/rooms/good_url',
            'financial_inputs': {'purchase_price': 300000} # Example financial input
        }
        response = self.app.post('/api/underwriting/analyze', json=payload)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        mock_scrape_listing.assert_called_once_with('https://www.airbnb.com/rooms/good_url', allow_mock=False)
        MockAirbnbScraperClass.assert_called_once() # Check constructor
        mock_scraper_instance.find_comparable_listings.assert_called_once()
        # Check city/keyword extraction: address_neighborhood is "Mockville, MC" -> city="Mockville"
        # title "Mocked Test Property", num_bedrooms 2 -> keyword "2 bedrooms"
        self.assertEqual(mock_scraper_instance.find_comparable_listings.call_args[1]['city'], 'Mockville')
        self.assertEqual(mock_scraper_instance.find_comparable_listings.call_args[1]['keyword'], '2 bedrooms')

        mock_calculate_underwriting.assert_called_once_with(
            MOCK_SCRAPE_RESULT_SUCCESS,
            MOCK_COMPARABLES_RESULT,
            payload['financial_inputs']
        )

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["subject_property"], MOCK_SCRAPE_RESULT_SUCCESS)
        self.assertEqual(data["comparable_properties"], MOCK_COMPARABLES_RESULT)
        self.assertEqual(data["underwriting_analysis"], MOCK_CALCULATOR_RESULT)

    @patch('underwriting.scrape_airbnb_listing')
    def test_analyze_property_subject_scraper_failure(self, mock_scrape_listing):
        mock_scrape_listing.return_value = MOCK_SCRAPE_RESULT_ERROR # Simulate scraper failure for subject

        payload = {'airbnb_url': 'https://www.airbnb.com/rooms/fail_url'}
        response = self.app.post('/api/underwriting/analyze', json=payload)

        self.assertEqual(response.status_code, 502) # Bad Gateway from upstream error
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn("error", data)
        self.assertTrue("Failed to scrape subject property" in data["error"])
        self.assertTrue(MOCK_SCRAPE_RESULT_ERROR["error"] in data["error"])

    @patch('underwriting.scrape_airbnb_listing') # Mock subject property scrape
    @patch('underwriting.AirbnbScraper')      # Mock the scraper class for comparables
    def test_analyze_property_comparable_scraper_failure(self, MockAirbnbScraperClass, mock_scrape_listing):
        mock_scrape_listing.return_value = MOCK_SCRAPE_RESULT_SUCCESS # Subject property is fine

        mock_scraper_instance = MockAirbnbScraperClass.return_value
        mock_scraper_instance.find_comparable_listings.side_effect = Exception("Comps network error")

        # We still expect calculate_underwriting to be called, but with empty comps
        with patch('underwriting.calculate_underwriting') as mock_calc:
            mock_calc.return_value = MOCK_CALCULATOR_RESULT # It will proceed with empty comps

            payload = {'airbnb_url': 'https://www.airbnb.com/rooms/good_url'}
            response = self.app.post('/api/underwriting/analyze', json=payload)

            self.assertEqual(response.status_code, 200) # The route itself succeeds
            data = json.loads(response.data.decode('utf-8'))

            self.assertEqual(data["subject_property"], MOCK_SCRAPE_RESULT_SUCCESS)
            self.assertEqual(data["comparable_properties"], []) # Comps search failed, so it's empty
            mock_calc.assert_called_once_with(MOCK_SCRAPE_RESULT_SUCCESS, [], {}) # Called with empty comps

    def test_analyze_property_missing_url(self):
        response = self.app.post('/api/underwriting/analyze', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["error"], "airbnb_url is required")

    def test_analyze_property_invalid_url_format(self):
        response = self.app.post('/api/underwriting/analyze', json={'airbnb_url': 'htp://notaurl.com'})
        self.assertEqual(response.status_code, 400) # From basic validation in underwriting.py
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["error"], "Invalid Airbnb URL format")

    def test_test_calculator_route_success(self):
        payload = {
            "mock_subject": {"price_per_night": 100, "num_bedrooms": 3, "cleaning_fee": 50},
            "mock_comparables": [{"price_per_night": 90}, {"price_per_night": 110}],
            "financial_inputs": {"purchase_price": 200000}
        }
        response = self.app.post('/api/underwriting/test-calculator', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["status"], "success")
        self.assertIn("test_results", data)
        self.assertIn("investment_summary", data["test_results"]) # Check for calculator output structure

    def test_test_calculator_route_empty_payload(self):
        # Test with empty payload, should use defaults in calculator for mock data
        # and default FinancialInputs
        response = self.app.post('/api/underwriting/test-calculator', json={})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data["status"], "success")
        self.assertIn("test_results", data)
        # Default purchase price if not in mock_subject and financial_inputs is 0 is 250000
        self.assertEqual(data["test_results"]["assumptions"]["purchase_price"], 250000.0)


if __name__ == '__main__':
    unittest.main()
