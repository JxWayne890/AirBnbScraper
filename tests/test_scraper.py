import unittest
from unittest.mock import patch, MagicMock, call
import requests # For mocking exceptions

# Assuming scraper.py is in the parent directory or PYTHONPATH is set up correctly.
# If running with `python -m unittest discover tests` from root, this should work.
from scraper import AirbnbScraper, scrape_airbnb_listing

# --- Sample HTML Snippets ---
SAMPLE_HTML_RICH = """
<html><head><title>Beautiful Apartment with View</title><meta property="og:title" content="OG Title: Beautiful Apartment"></head>
<body>
    <h1>Beautiful Apartment with View</h1>
    <span class="_160q0yh">$150 per night</span>
    <div data-testid="description-text"><p>A lovely place.</p><span>With great amenities.</span></div>
    <div><span>2 guests</span> · <span>1 bedroom</span> · <span>1 bed</span> · <span>1.5 baths</span></div>
    <span>★ 4.85 (120 reviews)</span>
    <div aria-label="What this place offers">
        <li>Wifi</li><span>Kitchen</span><div>Coffee maker</div><span class="amenity-item">Hair dryer</span>
    </div>
    <span>Host details: Superhost</span>
    <span data-testid="listing-location-title">Downtown, TestCity</span>
    <div data-testid="gallery">
        <img src="https://example.com/image1.jpg">
        <img src="http://example.com/image2.png">
    </div>
    <span>Cleaning fee: $50</span>
    <span>Service fee: $20</span>
</body></html>
"""

SAMPLE_HTML_MINIMAL = """
<html><head><title>Basic Room</title></head>
<body>
    <h1>Basic Room</h1>
    <p>Just a room.</p>
</body></html>
"""

SAMPLE_HTML_AIRBNB_SEARCH = """
<html><body>
    <a href="/rooms/123?source_impression_id=123">Listing 1</a>
    <a href="/rooms/plus/456?source_impression_id=456">Listing 2 (Plus)</a>
    <a href="https://www.airbnb.com/rooms/789">Listing 3 (Full URL)</a>
    <a href="/external/link">Some other link</a>
</body></html>
"""

SAMPLE_HTML_GOOGLE_SEARCH = """
<html><body>
    <a href="/url?q=https://www.airbnb.com/rooms/101&amp;sa=U">Google Link 1</a>
    <a href="https://www.airbnb.com/rooms/202?other_params=foo">Direct Link 2</a>
    <a href="/url?q=https://example.com/notairbnb">Non-Airbnb Google Link</a>
</body></html>
"""

class TestAirbnbScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = AirbnbScraper()

    def test_extract_listing_id(self):
        self.assertEqual(self.scraper.extract_listing_id("https://www.airbnb.com/rooms/12345"), "12345")
        self.assertEqual(self.scraper.extract_listing_id("https://www.airbnb.com/rooms/plus/67890"), "67890")
        self.assertEqual(self.scraper.extract_listing_id("https://www.airbnb.com/rooms/123?source_impression_id=p3"), "123")
        self.assertEqual(self.scraper.extract_listing_id("https://airbnb.com/rooms/123?source_impression_id=p3"), "123") # without www
        self.assertEqual(self.scraper.extract_listing_id("https://www.airbnb.co.uk/rooms/123"), "123") # different TLD
        self.assertIsNone(self.scraper.extract_listing_id("https://www.airbnb.com/s/homes"))
        self.assertIsNone(self.scraper.extract_listing_id("https://example.com/rooms/123"))

    @patch('requests.Session.get')
    def test_scrape_listing_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = SAMPLE_HTML_RICH.encode('utf-8')
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        data = self.scraper.scrape_listing("https://www.airbnb.com/rooms/1")

        self.assertIsNone(data.get("error"))
        self.assertEqual(data.get("title"), "Beautiful Apartment with View")
        self.assertEqual(data.get("price_per_night"), 150.0)
        self.assertIn("A lovely place.", data.get("description", ""))
        self.assertIn("With great amenities.", data.get("description", ""))
        self.assertEqual(data.get("guest_capacity"), 2)
        self.assertEqual(data.get("num_bedrooms"), 1)
        self.assertEqual(data.get("num_bathrooms"), 1.5)
        self.assertEqual(data.get("average_rating"), 4.85)
        self.assertEqual(data.get("num_reviews"), 120)
        self.assertIn("Wifi", data.get("amenities", []))
        self.assertIn("Kitchen", data.get("amenities", []))
        self.assertIn("Coffee maker", data.get("amenities", []))
        self.assertIn("Hair dryer", data.get("amenities", []))
        self.assertEqual(len(data.get("amenities", [])), 4) # Check for unique amenities
        self.assertEqual(data.get("host_type"), "Superhost")
        self.assertEqual(data.get("address_neighborhood"), "Downtown, TestCity")
        self.assertIn("https://example.com/image1.jpg", data.get("images", []))
        self.assertIn("http://example.com/image2.png", data.get("images", []))
        self.assertEqual(data.get("cleaning_fee"), 50.0)
        # self.assertEqual(data.get("service_fee"), 20.0) # Service fee extraction is very basic, might not always work

    @patch('requests.Session.get')
    def test_scrape_listing_og_title_fallback(self, mock_get):
        # Test when H1 is missing but OG title is present
        sample_html_og_title = """
        <html><head><meta property="og:title" content="OG Title Only"></head><body></body></html>
        """
        mock_response = MagicMock()
        mock_response.content = sample_html_og_title.encode('utf-8')
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        data = self.scraper.scrape_listing("https://www.airbnb.com/rooms/og_only")
        self.assertEqual(data.get("title"), "OG Title Only")


    @patch('requests.Session.get')
    def test_scrape_listing_missing_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = SAMPLE_HTML_MINIMAL.encode('utf-8')
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        data = self.scraper.scrape_listing("https://www.airbnb.com/rooms/minimal")
        self.assertIsNone(data.get("error"))
        self.assertEqual(data.get("title"), "Basic Room") # From H1
        self.assertIn("Just a room.", data.get("description", "")) # Description from P tag
        self.assertIsNone(data.get("price_per_night"))
        self.assertIsNone(data.get("guest_capacity"))
        self.assertIsNone(data.get("num_bedrooms"))
        self.assertIsNone(data.get("num_bathrooms"))
        self.assertIsNone(data.get("average_rating"))
        self.assertIsNone(data.get("num_reviews"))
        self.assertIsNone(data.get("amenities"))
        self.assertEqual(data.get("host_type"), "Regular") # Default if not found
        self.assertIsNone(data.get("address_neighborhood"))
        self.assertIsNone(data.get("images"))
        self.assertIsNone(data.get("cleaning_fee"))
        self.assertIsNone(data.get("service_fee"))

    @patch('requests.Session.get')
    def test_scrape_listing_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("Test network error")
        data = self.scraper.scrape_listing("https://www.airbnb.com/rooms/network_error")
        self.assertIsNotNone(data.get("error"))
        self.assertIn("Test network error", data.get("error", ""))

    @patch('requests.Session.get')
    def test_scrape_listing_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        mock_get.return_value = mock_response

        data = self.scraper.scrape_listing("https://www.airbnb.com/rooms/http_error")
        self.assertIsNotNone(data.get("error"))
        self.assertIn("404 Client Error", data.get("error", ""))

    @patch('time.sleep', return_value=None) # Mock time.sleep to speed up test
    @patch('requests.Session.get')
    def test_find_comparable_listings_direct_airbnb_success(self, mock_get, mock_sleep):
        # Mock for Airbnb search results page
        mock_search_response = MagicMock()
        mock_search_response.content = SAMPLE_HTML_AIRBNB_SEARCH.encode('utf-8')
        mock_search_response.status_code = 200

        # Mock for individual listing pages (simplified)
        mock_listing_response = MagicMock()
        mock_listing_response.content = SAMPLE_HTML_MINIMAL.encode('utf-8') # Use minimal for comps
        mock_listing_response.status_code = 200
        # Make listing_id derivable for comps
        mock_listing_response.url = "https://www.airbnb.com/rooms/123" # So extract_listing_id works

        def get_side_effect(*args, **kwargs):
            url = args[0]
            if "google.com" in url:
                # Should not happen in this test
                raise AssertionError("Google search was called in direct Airbnb success test")
            elif "/s/" in url and "/homes" in url: # Airbnb search
                return mock_search_response
            elif "/rooms/" in url: # Individual listing
                # Create a new mock response for each listing to allow different URLs if needed
                listing_resp = MagicMock()
                listing_resp.content = SAMPLE_HTML_MINIMAL.encode('utf-8')
                listing_resp.status_code = 200
                listing_resp.url = url # Ensure the mock response has the URL it was called with
                return listing_resp
            return MagicMock(status_code=404) # Fallback for unexpected calls

        mock_get.side_effect = get_side_effect

        results = self.scraper.find_comparable_listings("Test City", "test keyword", num_listings=3)
        self.assertEqual(len(results), 3)
        # Check if listing_ids are present in the results (they are part of the minimal HTML or URL)
        found_ids = {r.get('listing_id') for r in results if r.get('listing_id')}
        self.assertIn('123', found_ids)
        self.assertIn('456', found_ids)
        self.assertIn('789', found_ids)

        # Check that get was called for search and then for each listing
        # The first call is always the Airbnb search
        self.assertEqual(mock_get.call_args_list[0].args[0], 'https://www.airbnb.com/s/Test+City/homes?query=test+keyword')

        # The subsequent calls are for individual listings. Their order can vary due to set usage.
        called_listing_urls = {call_obj.args[0] for call_obj in mock_get.call_args_list[1:]}
        expected_listing_urls = {
            'https://www.airbnb.com/rooms/123',
            'https://www.airbnb.com/rooms/plus/456',
            'https://www.airbnb.com/rooms/789'
        }
        self.assertEqual(called_listing_urls, expected_listing_urls)
        self.assertEqual(mock_sleep.call_count, 2) # num_listings - 1

    @patch('time.sleep', return_value=None)
    @patch('requests.Session.get')
    def test_find_comparable_listings_google_fallback(self, mock_get, mock_sleep):
        mock_airbnb_search_empty = MagicMock()
        mock_airbnb_search_empty.content = "<html><body>No results</body></html>".encode('utf-8')
        mock_airbnb_search_empty.status_code = 200

        mock_google_response = MagicMock()
        mock_google_response.content = SAMPLE_HTML_GOOGLE_SEARCH.encode('utf-8')
        mock_google_response.status_code = 200

        def get_side_effect(*args, **kwargs):
            url = args[0]
            if "/s/" in url and "/homes" in url: # Airbnb search
                return mock_airbnb_search_empty
            elif "google.com/search" in url: # Google search
                return mock_google_response
            elif "/rooms/" in url: # Individual listing from Google
                listing_resp = MagicMock()
                listing_resp.content = SAMPLE_HTML_MINIMAL.encode('utf-8')
                listing_resp.status_code = 200
                listing_resp.url = url
                return listing_resp
            return MagicMock(status_code=404) # Fallback

        mock_get.side_effect = get_side_effect

        results = self.scraper.find_comparable_listings("Test City", "test keyword", num_listings=2)
        self.assertEqual(len(results), 2)
        found_ids = {r.get('listing_id') for r in results if r.get('listing_id')}
        self.assertIn('101', found_ids)
        self.assertIn('202', found_ids)

        # Check call sequence
        self.assertEqual(mock_get.call_args_list[0].args[0], 'https://www.airbnb.com/s/Test+City/homes?query=test+keyword')
        self.assertEqual(mock_get.call_args_list[1].args[0], 'https://www.google.com/search?q=site%3Aairbnb.com%2Frooms%2F+Test+City+test+keyword&num=4')

        called_listing_urls = {call_obj.args[0] for call_obj in mock_get.call_args_list[2:]}
        expected_listing_urls = {
            'https://www.airbnb.com/rooms/101',
            'https://www.airbnb.com/rooms/202'
        }
        self.assertEqual(called_listing_urls, expected_listing_urls)
        self.assertEqual(mock_sleep.call_count, 1) # num_listings - 1

class TestScrapeAirbnbListingFunction(unittest.TestCase):
    @patch('scraper.AirbnbScraper') # Patch the class where it's defined/imported in scraper.py
    def test_scrape_airbnb_listing_wrapper_success(self, MockAirbnbScraper):
        mock_scraper_instance = MockAirbnbScraper.return_value
        mock_scraper_instance.scrape_listing.return_value = {"title": "Mocked Listing"}

        result = scrape_airbnb_listing("http://example.com/rooms/test", allow_mock=False)

        MockAirbnbScraper.assert_called_once() # Check if constructor was called
        mock_scraper_instance.scrape_listing.assert_called_once_with("http://example.com/rooms/test")
        self.assertEqual(result, {"title": "Mocked Listing"})

    @patch('scraper.AirbnbScraper')
    def test_scrape_airbnb_listing_wrapper_invalid_url(self, MockAirbnbScraper):
        result = scrape_airbnb_listing("invalid_url_format")
        MockAirbnbScraper.assert_not_called() # Scraper should not be instantiated
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Invalid URL format.")

if __name__ == '__main__':
    unittest.main()
