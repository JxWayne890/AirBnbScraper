import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, List, Optional
import time
from urllib.parse import urljoin, quote_plus

# Configure logging
# BasicConfig should ideally be called only once at the application entry point.
# If this module is imported elsewhere, this might reconfigure.
# For robustness, consider checking if handlers are already configured for the root logger.
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirbnbScraper:
    """
    A scraper for fetching details from Airbnb listing URLs and finding comparable listings.
    It uses requests and BeautifulSoup for HTML parsing and does not rely on Selenium or headless browsers.
    """
    def __init__(self, session: Optional[requests.Session] = None):
        """
        Initializes the AirbnbScraper.

        Args:
            session: An optional requests.Session object. If not provided, a new one is created.
        """
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        })

    def extract_listing_id(self, url: str) -> Optional[str]:
        """
        Extracts the Airbnb listing ID from a given URL.

        Args:
            url: The Airbnb listing URL.

        Returns:
            The extracted listing ID as a string, or None if not found.
        """
        # Common URL patterns: /rooms/<id> or /rooms/plus/<id>
        match = re.search(r'/rooms/(?:plus/)?(\d+)', url)
        if match:
            return match.group(1)
        # Fallback for URLs that might have listing_id as a query parameter (less common for direct listing URLs)
        match = re.search(r'listing_id=(\d+)', url)
        if match:
            return match.group(1)
        logger.warning(f"Could not extract listing ID from URL: {url}")
        return None

    def scrape_listing(self, url: str) -> Dict[str, any]:
        """
        Scrapes a single Airbnb listing URL for its details.

        Args:
            url: The full URL of the Airbnb listing.

        Returns:
            A dictionary containing the scraped data. Keys include:
            'listing_url', 'listing_id', 'title', 'price_per_night', 'currency',
            'description', 'guest_capacity', 'num_bedrooms', 'num_bathrooms',
            'average_rating', 'num_reviews', 'amenities', 'host_type',
            'address_neighborhood', 'images', 'cleaning_fee', 'service_fee'.
            If an error occurs during scraping, an 'error' key will be present in the dictionary.
        """
        data: Dict[str, any] = {"listing_url": url, "scrape_timestamp": time.time()} # Added timestamp

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {url}: {e}")
            data["error"] = f"Network error fetching URL: {e}"
            return data
        except Exception as e: # Catch broader exceptions during soup parsing
            logger.error(f"Error parsing HTML for URL {url}: {e}", exc_info=True)
            data["error"] = f"HTML parsing error: {e}"
            return data

        # Extract Listing ID
        try:
            data["listing_id"] = self.extract_listing_id(url)
        except Exception as e: # Should be robust, but good practice
            logger.warning(f"Could not extract listing_id for {url}: {e}", exc_info=True)
            data["listing_id"] = None

        # Title
        try:
            # Selector Note: Prioritizes H1, then 'og:title' meta tag.
            title_tag = soup.find('h1')
            if title_tag:
                data["title"] = title_tag.get_text(strip=True)
            else:
                title_tag_meta = soup.find('meta', property='og:title')
                if title_tag_meta and title_tag_meta.get('content'):
                    data["title"] = title_tag_meta.get('content', strip=True)
                else:
                    logger.warning(f"Title not found for {url}")
                    data["title"] = None
        except Exception as e:
            logger.warning(f"Could not extract title for {url}: {e}", exc_info=True)
            data["title"] = None

        # Price per night (and currency)
        try:
            # Selector Note: '_160q0yh' is an example class, likely to change. Regex fallback is more robust.
            price_tag = soup.find('span', class_='_160q0yh')
            if not price_tag:
                 price_tag = soup.find('span', string=re.compile(r'[\$€£¥]\s*\d+')) # Looks for currency symbol then number

            if price_tag:
                price_text = price_tag.get_text(strip=True)
                match = re.search(r'([\$€£¥]?)\s*([\d,.]+)', price_text)
                if match:
                    data["price_per_night"] = float(match.group(2).replace(',', ''))
                    data["currency"] = match.group(1) if match.group(1) else None
                else:
                    data["price_per_night"] = None
                    data["currency"] = None
                    logger.warning(f"Could not parse price_text: '{price_text}' from {url}")
            else:
                logger.warning(f"Price not found for {url}")
                data["price_per_night"] = None
                data["currency"] = None
        except Exception as e:
            logger.warning(f"Could not extract price for {url}: {e}", exc_info=True)
            data["price_per_night"] = None
            data["currency"] = None

        # Description
        try:
            # Selector Note: 'data-testid' is good if stable. Regex class search is a fallback.
            description_tag = soup.find('div', {'data-testid': 'description-text'})
            if not description_tag:
                description_tag = soup.find('div', class_=re.compile(r'description'))

            if description_tag:
                data["description"] = "\n".join([p.get_text(strip=True) for p in description_tag.find_all(['p', 'span']) if p.get_text(strip=True)])
            else:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    data["description"] = meta_desc.get('content', strip=True)
                else:
                    logger.warning(f"Description not found for {url}")
                    data["description"] = None
        except Exception as e:
            logger.warning(f"Could not extract description for {url}: {e}", exc_info=True)
            data["description"] = None

        # Room Details: Guest capacity, Bedrooms, Bathrooms
        try:
            # Selector Note: These details are often grouped. Looking for a general container first.
            # Class 'host-profile' is a placeholder. Regex for "X guests" is a common pattern.
            room_info_tag_text = None
            room_info_container = soup.find(string=re.compile(r'\d+\s+guests?'))
            if room_info_container:
                 # Try to find a parent element that contains all room details
                 parent_candidate = room_info_container.parent
                 for _ in range(3): # Check up to 3 levels up
                    if parent_candidate and ("bedroom" in parent_candidate.get_text(strip=True, separator=" ").lower() or "bath" in parent_candidate.get_text(strip=True, separator=" ").lower()):
                        room_info_tag_text = parent_candidate.get_text(separator=' ', strip=True)
                        break
                    if parent_candidate: parent_candidate = parent_candidate.parent
                    else: break

            if room_info_tag_text:
                guests_match = re.search(r'(\d+)\s+guest', room_info_tag_text, re.IGNORECASE)
                data["guest_capacity"] = int(guests_match.group(1)) if guests_match else None

                bedrooms_match = re.search(r'(\d+)\s+bedroom', room_info_tag_text, re.IGNORECASE)
                data["num_bedrooms"] = int(bedrooms_match.group(1)) if bedrooms_match else None

                bathrooms_match = re.search(r'(\d+(\.\d+)?)\s+bath', room_info_tag_text, re.IGNORECASE)
                data["num_bathrooms"] = float(bathrooms_match.group(1)) if bathrooms_match else None
            else:
                logger.info(f"Combined room info not found for {url}, trying individual selectors via helper.")
                data["guest_capacity"] = self._extract_text_from_element(soup, string_pattern=re.compile(r'(\d+)\s+guests?'), extract_group=1, return_type=int)
                data["num_bedrooms"] = self._extract_text_from_element(soup, string_pattern=re.compile(r'(\d+)\s+bedrooms?'), extract_group=1, return_type=int)
                data["num_bathrooms"] = self._extract_text_from_element(soup,string_pattern=re.compile(r'(\d+(\.\d+)?)\s+baths?'), extract_group=1, return_type=float)
        except Exception as e:
            logger.warning(f"Could not extract room details for {url}: {e}", exc_info=True)
            data["guest_capacity"] = None
            data["num_bedrooms"] = None
            data["num_bathrooms"] = None

        # Reviews and Rating
        try:
            # Selector Note: Combined rating/review text is common.
            rating_review_text = None
            rating_review_tag = soup.find(string=re.compile(r'reviews\)?$|\d+\s+review'))
            if rating_review_tag:
                parent_candidate = rating_review_tag.parent
                for _ in range(2): # Check a couple of parents
                    if parent_candidate and ("★" in parent_candidate.get_text() or re.search(r'\d\.\d', parent_candidate.get_text())):
                        rating_review_text = parent_candidate.get_text(strip=True)
                        break
                    if parent_candidate: parent_candidate = parent_candidate.parent
                    else: break

            if rating_review_text:
                rating_match = re.search(r'[★]?\s*([\d.]+)', rating_review_text)
                data["average_rating"] = float(rating_match.group(1)) if rating_match else None
                reviews_match = re.search(r'\(?(\d+)\s+review', rating_review_text, re.IGNORECASE)
                data["num_reviews"] = int(reviews_match.group(1)) if reviews_match else None
            else:
                logger.info(f"Combined rating/review span not found for {url}. Trying individual.")
                data["average_rating"] = self._extract_text_from_element(soup, string_pattern=re.compile(r'★\s*([\d.]+)'), extract_group=1, return_type=float)
                data["num_reviews"] = self._extract_text_from_element(soup, string_pattern=re.compile(r'\(?(\d+)\s+reviews?\)'), extract_group=1, return_type=int)
                if not data["num_reviews"]: # Fallback if no parenthesis
                     data["num_reviews"] = self._extract_text_from_element(soup, string_pattern=re.compile(r'(\d+)\s+reviews?'), extract_group=1, return_type=int)
        except Exception as e:
            logger.warning(f"Could not extract reviews/ratings for {url}: {e}", exc_info=True)
            data["num_reviews"] = None
            data["average_rating"] = None

        # Amenities
        try:
            amenities = []
            # Selector Note: 'aria-label' for section and then generic items. Robust if aria-label stays.
            amenities_section = soup.find('div', attrs={'aria-label': re.compile(r"What this place offers", re.IGNORECASE)})
            if not amenities_section:
                amenities_section = soup.find('div', class_=re.compile(r"amenities|Amenities")) # Fallback

            if amenities_section:
                for item in amenities_section.find_all(['li', 'span', 'div'], class_=re.compile(r"item|amenity", re.IGNORECASE)):
                    text = item.get_text(strip=True)
                    if text and len(text) > 2 and len(text) < 50: # Filter out very short/long strings
                        amenities.append(text)
            data["amenities"] = list(set(amenities)) if amenities else None
            if not data["amenities"]: logger.info(f"No amenities extracted with primary selectors for {url}")
        except Exception as e:
            logger.warning(f"Could not extract amenities for {url}: {e}", exc_info=True)
            data["amenities"] = None

        # Host type
        try:
            # Selector Note: Searching for "Superhost" string is fairly reliable.
            superhost_tag = soup.find(string=re.compile(r'Superhost', re.IGNORECASE))
            data["host_type"] = "Superhost" if superhost_tag else "Regular"
        except Exception as e:
            logger.warning(f"Could not determine host type for {url}: {e}", exc_info=True)
            data["host_type"] = "Regular" # Default

        # Address or Neighborhood
        try:
            # Selector Note: 'data-testid' is preferred. 'og:locality' is a good fallback.
            address_tag = soup.find(attrs={'data-testid': 'listing-location-title'})
            if not address_tag:
                 address_tag = soup.find('span', class_=re.compile(r'location|address', re.IGNORECASE))

            if address_tag:
                data["address_neighborhood"] = address_tag.get_text(strip=True)
            else:
                meta_region = soup.find('meta', property='og:locality')
                if meta_region and meta_region.get('content'):
                     data["address_neighborhood"] = meta_region.get('content')
                else:
                    logger.warning(f"Address/Neighborhood not found for {url}")
                    data["address_neighborhood"] = None
        except Exception as e:
            logger.warning(f"Could not extract address/neighborhood for {url}: {e}", exc_info=True)
            data["address_neighborhood"] = None

        # Images
        try:
            images = []
            # Selector Note: 'data-testid' for gallery is good. Then find 'img' tags.
            main_image_area = soup.find('div', {'data-testid': re.compile(r'gallery|photos', re.IGNORECASE)})
            if not main_image_area:
                main_image_area = soup.body # Fallback to whole body if specific gallery not found

            if main_image_area:
                for img_tag in main_image_area.find_all('img', src=True, limit=5):
                    src = img_tag['src']
                    if src and src.startswith('http') and len(src) > 10: # Basic validation
                        images.append(src)
            data["images"] = list(set(images)) if images else None
            if not data["images"]: logger.info(f"No images extracted for {url}")
        except Exception as e:
            logger.warning(f"Could not extract images for {url}: {e}", exc_info=True)
            data["images"] = None

        # Fees (Cleaning, Service)
        try:
            # Selector Note: Finding text "Cleaning fee" then looking in parent is heuristic.
            cleaning_fee_text_el = soup.find(string=re.compile(r'Cleaning fee', re.IGNORECASE))
            if cleaning_fee_text_el:
                parent_container = cleaning_fee_text_el.find_parent()
                if parent_container:
                    fee_text_match = re.search(r'[\$€£¥]?\s*([\d,.]+)', parent_container.get_text())
                    if fee_text_match: data["cleaning_fee"] = float(fee_text_match.group(1).replace(',', ''))
                    else: data["cleaning_fee"] = None
                else: data["cleaning_fee"] = None
            else:
                data["cleaning_fee"] = None
                logger.info(f"Cleaning fee string not directly found for {url}")

            service_fee_text_el = soup.find(string=re.compile(r'Service fee', re.IGNORECASE))
            if service_fee_text_el:
                parent_container = service_fee_text_el.find_parent()
                if parent_container:
                    fee_text_match = re.search(r'[\$€£¥]?\s*([\d,.]+)', parent_container.get_text())
                    if fee_text_match: data["service_fee"] = float(fee_text_match.group(1).replace(',', ''))
                    else: data["service_fee"] = None
                else: data["service_fee"] = None
            else:
                data["service_fee"] = None
                logger.info(f"Service fee string not directly found for {url}")
        except Exception as e:
            logger.warning(f"Could not extract fees for {url}: {e}", exc_info=True)
            data["cleaning_fee"] = None
            data["service_fee"] = None

        logger.info(f"Finished scraping for {url}. Title: {data.get('title', 'N/A')}, Price: {data.get('price_per_night', 'N/A')}")
        return data

    def find_comparable_listings(self, city: str, keyword: str, num_listings: int = 5) -> List[Dict[str, any]]:
        """
        Finds and scrapes comparable Airbnb listings.
        It first attempts a direct search on Airbnb. If insufficient results are found,
        it falls back to using Google Search with 'site:airbnb.com/rooms/'.

        Args:
            city: The city to search for listings in.
            keyword: A keyword to refine the search (e.g., "2 bedroom apartment", "cabin").
            num_listings: The target number of comparable listings to find and scrape.

        Returns:
            A list of dictionaries, where each dictionary contains the scraped data
            for a comparable listing, similar to the output of `scrape_listing`.
        """
        logger.info(f"Starting comparable listings search for city='{city}', keyword='{keyword}', num_listings={num_listings}")
        found_urls: set[str] = set()
        comparable_data: List[Dict[str, any]] = []

        # 1. Direct Airbnb Search Attempt
        try:
            encoded_city = quote_plus(city)
            encoded_keyword = quote_plus(keyword)
            # Selector Note: Airbnb search URL structure can change. This is a common pattern.
            search_url = f"https://www.airbnb.com/s/{encoded_city}/homes?query={encoded_keyword}"
            logger.info(f"Attempting direct Airbnb search with URL: {search_url}")

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Selector Note: Links are typically in <a> tags, href starting with /rooms/.
            # The specificity of 'a[href^="/rooms/"]' helps.
            for link_tag in soup.find_all('a', href=True):
                href = link_tag['href']
                if re.match(r'/rooms/(?:plus/)?\d+', href): # Matches /rooms/<id> and /rooms/plus/<id>
                    full_url = urljoin("https://www.airbnb.com", href)
                    found_urls.add(full_url.split('?')[0]) # Remove query parameters for uniqueness
                    if len(found_urls) >= num_listings:
                        break
            logger.info(f"Found {len(found_urls)} unique URLs from direct Airbnb search.")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Direct Airbnb search request failed for '{city} - {keyword}': {e}")
        except Exception as e:
            logger.error(f"Error parsing direct Airbnb search results for '{city} - {keyword}': {e}", exc_info=True)

        # 2. Google Search Fallback
        if len(found_urls) < num_listings: # Try Google if not enough URLs from direct search
            logger.info(f"Direct Airbnb search yielded {len(found_urls)} results (target {num_listings}). Falling back to Google Search.")
            try:
                google_query = f"site:airbnb.com/rooms/ {city} {keyword}"
                encoded_google_query = quote_plus(google_query)
                # Request slightly more results from Google to allow for filtering non-listing URLs
                google_search_url = f"https://www.google.com/search?q={encoded_google_query}&num={num_listings * 2 + 5}"

                logger.info(f"Attempting Google search with URL: {google_search_url}")
                response = self.session.get(google_search_url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                # Selector Note: Google search results structure can change frequently.
                # This looks for <a> tags and then checks the href.
                for link_tag in soup.find_all('a', href=True):
                    href = link_tag['href']
                    if 'airbnb.com/rooms/' in href:
                        if href.startswith('/url?q='): # Google redirect URL
                            actual_url_match = re.search(r'/url\?q=([^&]+)', href)
                            if actual_url_match: href = actual_url_match.group(1)

                        if href.startswith('https://www.airbnb.com/rooms/') and self.extract_listing_id(href):
                            clean_url = href.split('?')[0].split('#')[0]
                            found_urls.add(clean_url)
                            if len(found_urls) >= num_listings:
                                break
                logger.info(f"Found {len(found_urls)} unique URLs after Google search fallback for '{city} - {keyword}'.")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Google search request failed for '{city} - {keyword}': {e}")
            except Exception as e:
                logger.error(f"Error parsing Google search results for '{city} - {keyword}': {e}", exc_info=True)

        if not found_urls:
            logger.warning(f"No listing URLs found for city='{city}', keyword='{keyword}' after all attempts.")
            return []

        # 3. Scrape Collected URLs
        logger.info(f"Proceeding to scrape details for {min(len(found_urls), num_listings)} URLs for '{city} - {keyword}'.")
        urls_to_scrape = list(found_urls)[:num_listings]

        for i, url_to_scrape in enumerate(urls_to_scrape):
            logger.info(f"Scraping comparable listing {i+1}/{len(urls_to_scrape)}: {url_to_scrape}")
            try:
                listing_data = self.scrape_listing(url_to_scrape)
                if listing_data and not listing_data.get("error"):
                    comparable_data.append(listing_data)
                elif listing_data.get("error"): # Log error from scrape_listing if present
                     logger.warning(f"Failed to scrape comparable listing {url_to_scrape}: {listing_data.get('error')}")

                if i < len(urls_to_scrape) - 1:
                    sleep_duration = 2
                    logger.debug(f"Sleeping for {sleep_duration} seconds before next comparable scrape.")
                    time.sleep(sleep_duration)
            except Exception as e: # Catch any other unexpected errors during this loop
                logger.error(f"Unhandled error scraping individual comparable listing {url_to_scrape}: {e}", exc_info=True)

        logger.info(f"Successfully scraped {len(comparable_data)} comparable listings for '{city} - {keyword}'.")
        return comparable_data

    def _extract_text_from_element(self, soup: BeautifulSoup,
                                 selector: Optional[str] = None,
                                 string_pattern: Optional[re.Pattern] = None,
                                 extract_group: int = 0,
                                 return_type=str,
                                 attribute: Optional[str]=None) -> Optional[any]:
        """
        Helper to find an element and extract its text or an attribute value.
        Can find by CSS selector or by a regex pattern within element text.

        Args:
            soup: BeautifulSoup object to search within.
            selector: CSS selector to find the element.
            string_pattern: Regex pattern to search for in element's text content.
                            If `extract_group` > 0, that group is returned.
            extract_group: Which regex group to extract if `string_pattern` is used.
            return_type: The type to convert the extracted value to (e.g., int, float).
            attribute: If provided, extract this attribute's value instead of text.

        Returns:
            The extracted and typed value, or None if not found or on error.
        """
        try:
            element = None
            if selector:
                element = soup.find(selector)
            elif string_pattern and not attribute: # String pattern search on text
                element = soup.find(string=string_pattern)
                if element and extract_group > 0:
                    match = string_pattern.search(element.string) # type: ignore
                    text_to_return = match.group(extract_group) if match else None
                    return return_type(text_to_return) if text_to_return and return_type else text_to_return

            if element:
                value_to_process: Optional[str] = None
                if attribute:
                    value_to_process = element.get(attribute)
                else:
                    value_to_process = element.get_text(strip=True)

                if value_to_process is not None:
                    if string_pattern and not selector and not attribute and extract_group == 0: # pattern on full text of found element
                         match = string_pattern.search(value_to_process)
                         if match: # if pattern is just for validation or group 0 is fine
                            value_to_process = match.group(extract_group)
                         else: # pattern did not match element text
                            return None
                    return return_type(value_to_process) if value_to_process and return_type else value_to_process
        except Exception as e:
            logger.debug(f"Helper extraction error: Selector='{selector}', Pattern='{string_pattern}', Attr='{attribute}', Error='{e}'")
        return None


def scrape_airbnb_listing(url: str, allow_mock: bool = False) -> Dict[str, any]:
    """
    Main standalone function to scrape a single Airbnb listing.
    It creates an AirbnbScraper instance and calls its scrape_listing method.

    Args:
        url: The URL of the Airbnb listing to scrape.
        allow_mock: If True, allows returning mock data (functionality not fully implemented here).

    Returns:
        A dictionary containing the scraped data from the listing.
        Includes an 'error' key if scraping fails.
    """
    if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
        logger.error(f"Invalid URL provided to scrape_airbnb_listing: {url}")
        return {"error": "Invalid URL format."}

    # Mocking logic placeholder
    # if allow_mock and is_mock_url(url): # Define is_mock_url and load_mock_data if needed
    #     logger.info(f"Returning mock data for URL: {url}")
    #     return load_mock_data(url)

    scraper = AirbnbScraper()
    try:
        data = scraper.scrape_listing(url)
    except Exception as e:
        # This catch is broad; specific errors are handled within scrape_listing.
        # This acts as a final safeguard.
        logger.critical(f"Unhandled exception during scraping process for {url}: {e}", exc_info=True)
        return {"error": f"Critical error in scraping process: {e}", "listing_url": url}
    return data

if __name__ == '__main__':
    # Example Usage (for testing purposes during development)
    # Note: Scraping Airbnb is against their TOS and may lead to IP blocks.
    # Use responsibly and ethically, primarily for learning and with non-aggressive timing.

    # test_url = "https://www.airbnb.com/rooms/33571268" # Example valid URL
    # logger.info(f"Starting test scrape for URL: {test_url}")
    # scraped_data = scrape_airbnb_listing(test_url)

    # if scraped_data.get("error"):
    #     logger.error(f"Test scraping failed: {scraped_data.get('error')}")
    # else:
    #     logger.info("Test scraping successful. Data (selected fields):")
    #     for key, value in scraped_data.items():
    #         if key in ["title", "price_per_night", "currency", "num_bedrooms", "num_bathrooms",
    #                      "average_rating", "num_reviews", "listing_id", "address_neighborhood",
    #                      "cleaning_fee", "host_type"]:
    #             logger.info(f"  {key}: {value}")
    #         elif key == "description" and value:
    #              logger.info(f"  description: {value[:100]}...")
    #         elif key == "amenities" and value:
    #              logger.info(f"  amenities (first 3): {value[:3]}...")
    #         elif key == "images" and value:
    #              logger.info(f"  images (first 1): {value[:1]}...")

    # Test find_comparable_listings
    # scraper_instance_for_comps = AirbnbScraper()
    # city_test = "Kyoto" # Example city
    # keyword_test = "machiya house" # Example keyword
    # num_comps_to_find = 3
    # logger.info(f"Starting test for find_comparable_listings with city='{city_test}', keyword='{keyword_test}', num_listings={num_comps_to_find}")
    # comparable_listings_data = scraper_instance_for_comps.find_comparable_listings(city_test, keyword_test, num_listings=num_comps_to_find)

    # if comparable_listings_data:
    #     logger.info(f"Found {len(comparable_listings_data)} comparable listings:")
    #     for idx, listing_data in enumerate(comparable_listings_data):
    #         logger.info(f"  Comp {idx+1} Title: {listing_data.get('title', 'N/A')}, Price: {listing_data.get('price_per_night', 'N/A')}, URL: {listing_data.get('listing_url')}")
    # else:
    #     logger.warning(f"No comparable listings found in test for {city_test} with keyword {keyword_test}.")

    logger.info("Scraper module test run/example completed.")
