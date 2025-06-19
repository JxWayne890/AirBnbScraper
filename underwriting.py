"""
Flask blueprint for the underwriting API endpoints.
Handles requests for property analysis, scraper testing, calculator testing,
health checks, and API documentation.
"""
from flask import Blueprint, request, jsonify
from scraper import scrape_airbnb_listing, AirbnbScraper
from calculator import calculate_underwriting
import logging
import re # For city/keyword extraction

# Configure logging for this blueprint
# BasicConfig should ideally be called only once at the application entry point.
if not logging.getLogger().hasHandlers() or not logging.getLogger(__name__).hasHandlers(): # Check specific logger
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

underwriting_bp = Blueprint('underwriting', __name__)

def extract_city_from_address(address_string: str) -> str:
    """
    Simple heuristic to extract a potential city name from an address string.
    This is a basic approach and might need enhancement for production accuracy,
    potentially using a geocoding service or more sophisticated parsing.

    Args:
        address_string: The address or neighborhood string (e.g., "Austin, TX, United States").

    Returns:
        A string representing the extracted city name, or "Unknown" if extraction fails.
    """
    if not address_string:
        return "Unknown"
    parts = [part.strip() for part in address_string.split(',')]
    if not parts:
        return "Unknown"

    # Heuristic:
    # - If "City, State/Country", city is parts[0].
    # - If "Neighborhood, City, State/Country", city is often parts[1].
    # - If only one part, assume it's the city.
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0]
    if len(parts) > 2:
        # This is a common pattern, but not guaranteed.
        return parts[1]
    return parts[0] # Fallback, though less likely to be correct for multi-part addresses not fitting above.


def generate_keyword_from_details(details: dict) -> str:
    """
    Generates a search keyword string based on property details.
    Prioritizes number of bedrooms, then falls back to property type from title,
    then guest capacity, and finally a generic term.

    Args:
        details: A dictionary of property details, typically from `scrape_airbnb_listing`.
                 Expected keys: 'num_bedrooms', 'title', 'guest_capacity'.

    Returns:
        A string to be used as a search keyword.
    """
    title = details.get('title', '').lower()
    num_bedrooms = details.get('num_bedrooms')

    if num_bedrooms is not None:
        try:
            beds = int(num_bedrooms) # Ensure it's an integer
            if beds == 0: return "studio apartment"
            if beds == 1: return "1 bedroom"
            return f"{beds} bedrooms"
        except (ValueError, TypeError): # Handle cases where num_bedrooms might not be a valid number string
            logger.warning(f"Could not parse num_bedrooms '{num_bedrooms}' as integer for keyword generation.")
            # Fall through to title/guest capacity based keyword

    # Fallback to property type from title
    common_types = ['apartment', 'condo', 'loft', 'house', 'cabin', 'villa', 'townhouse', 'bungalow']
    for prop_type in common_types:
        if prop_type in title:
            return prop_type

    # Fallback to guest capacity
    guest_capacity = details.get('guest_capacity')
    if guest_capacity is not None:
        try:
            guests = int(guest_capacity)
            return f"property for {guests} guests"
        except (ValueError, TypeError):
            logger.warning(f"Could not parse guest_capacity '{guest_capacity}' for keyword generation.")

    return "property" # Most generic fallback

@underwriting_bp.route('/analyze', methods=['POST'])
def analyze_property():
    """
    Analyzes an Airbnb property for investment potential.
    It scrapes data for the subject property, finds comparable listings,
    and then performs financial underwriting calculations.

    Request JSON Body:
        {
            "airbnb_url": "string (required) - URL of the Airbnb listing.",
            "num_comparables": "int (optional) - Number of comparable listings to find (default 5).",
            "financial_inputs": "object (optional) - Custom financial parameters (see FinancialInputs in calculator.py)."
        }

    Returns:
        JSON response with analysis results or an error message.
        Success (200): {'status': 'success', 'subject_property': {...},
                        'comparable_properties': [...], 'underwriting_analysis': {...},
                        'analysis_timestamp': ...}
        Error (400, 500, 502): {'error': 'Error message', 'status': 'error'}
    """
    try:
        payload = request.get_json()
        if not payload:
            logger.warning("Analyze request failed: No JSON payload provided.")
            return jsonify({'error': 'No JSON data provided', 'status': 'error'}), 400

        airbnb_url = payload.get('airbnb_url')
        if not airbnb_url:
            logger.warning("Analyze request failed: 'airbnb_url' missing from payload.")
            return jsonify({'error': 'airbnb_url is required', 'status': 'error'}), 400

        if not isinstance(airbnb_url, str) or 'airbnb.com' not in airbnb_url:
            logger.warning(f"Analyze request failed: Invalid Airbnb URL format for '{airbnb_url}'.")
            return jsonify({'error': 'Invalid Airbnb URL format', 'status': 'error'}), 400

        financial_inputs = payload.get('financial_inputs', {})
        num_comparables_to_find = payload.get('num_comparables', 5)
        if not isinstance(num_comparables_to_find, int) or num_comparables_to_find <= 0:
            logger.warning(f"Invalid num_comparables value '{num_comparables_to_find}', defaulting to 5.")
            num_comparables_to_find = 5


        logger.info(f"Starting analysis for URL: {airbnb_url}, finding up to {num_comparables_to_find} comparables.")

        # 1. Scrape the subject property
        logger.info(f"Scraping subject property details from: {airbnb_url}")
        subject_property_details = scrape_airbnb_listing(airbnb_url, allow_mock=False)

        if subject_property_details.get("error"):
            err_msg = subject_property_details.get('error')
            logger.error(f"Failed to scrape subject property {airbnb_url}: {err_msg}")
            return jsonify({'error': f"Failed to scrape subject property: {err_msg}", 'status': 'error'}), 502

        logger.info(f"Successfully scraped subject property: {subject_property_details.get('title', 'N/A')}")

        # 2. Find comparable properties
        comparable_properties = []
        city, keyword = "Unknown", "property" # Defaults

        address_or_neighborhood = subject_property_details.get('address_neighborhood')
        if address_or_neighborhood:
            city = extract_city_from_address(address_or_neighborhood)
        else:
            logger.warning(f"Address/neighborhood not found for subject property {airbnb_url}. City for comps search remains '{city}'.")

        keyword = generate_keyword_from_details(subject_property_details)
        logger.info(f"For comps search: City='{city}', Keyword='{keyword}'.")

        if city != "Unknown":
            try:
                logger.info(f"Searching for up to {num_comparables_to_find} comparable listings...")
                scraper_instance = AirbnbScraper()
                comparable_properties = scraper_instance.find_comparable_listings(
                    city=city, keyword=keyword, num_listings=num_comparables_to_find
                )
                logger.info(f"Found {len(comparable_properties)} comparable properties.")
            except Exception as e: # Catch errors from find_comparable_listings
                logger.error(f"Error finding comparable listings for {city} / {keyword}: {e}", exc_info=True)
                # Continue with analysis even if comps search fails; comparable_properties will be empty.
        else:
            logger.warning(f"Skipping comparable properties search for {airbnb_url} due to 'Unknown' city.")

        # 3. Perform underwriting calculation
        logger.info("Performing underwriting calculation...")
        analysis_results = calculate_underwriting(
            subject_property_details, comparable_properties, financial_inputs
        )
        logger.info("Underwriting calculation complete.")

        # 4. Return all results
        response_data = {
            'status': 'success',
            'subject_property': subject_property_details,
            'comparable_properties': comparable_properties,
            'underwriting_analysis': analysis_results,
            'analysis_timestamp': subject_property_details.get('scrape_timestamp', None)
        }
        logger.info(f"Analysis for {airbnb_url} completed successfully.")
        return jsonify(response_data), 200

    except Exception as e: # Catch-all for any other unexpected errors in the route
        current_url = payload.get('airbnb_url', 'unknown') if 'payload' in locals() else 'unknown'
        logger.error(f"Critical error during property analysis for URL '{current_url}': {e}", exc_info=True)
        return jsonify({'error': f'An unexpected internal server error occurred: {str(e)}', 'status': 'error'}), 500

@underwriting_bp.route('/test-scraper', methods=['GET', 'POST'])
def test_scraper():
    """
    Tests the Airbnb listing scraper for a given URL.
    Accepts 'airbnb_url' via query parameter (GET) or JSON/form body (POST).

    Returns:
        JSON response with scraped data or an error message.
        Success (200): {'status': 'success', 'scrape_results': {...}}
        Error (400, 500, 502): {'error': 'Error message', 'status': 'error'}
    """
    airbnb_url = None
    if request.method == 'GET':
        airbnb_url = request.args.get('airbnb_url')
    elif request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            airbnb_url = data.get('airbnb_url') if data else None
        else: # Fallback for form data
            airbnb_url = request.form.get('airbnb_url')

    if not airbnb_url:
        logger.warning("[TEST SCRAPER] Request failed: airbnb_url missing.")
        return jsonify({"error": "airbnb_url is required in query parameters (GET) or JSON/form body (POST)", 'status': 'error'}), 400

    logger.info(f"[TEST SCRAPER] Initiating scrape for URL: {airbnb_url}")

    try:
        scrape_results = scrape_airbnb_listing(airbnb_url, allow_mock=False)

        if not scrape_results: # Should always return a dict
            logger.error(f"[TEST SCRAPER] Scraper returned no data for {airbnb_url}.")
            return jsonify({'error': 'Scraper returned no data.', 'status': 'error'}), 500

        if scrape_results.get("error"):
            err_msg = scrape_results.get("error")
            logger.error(f"[TEST SCRAPER] Scraping failed for {airbnb_url}: {err_msg}")
            # Determine status code based on error type
            status_code = 502 if "fetching" in err_msg.lower() or "parsing" in err_msg.lower() or "Network error" in err_msg else 400
            return jsonify({"error": f"Failed to scrape Airbnb URL: {err_msg}", 'status': 'error'}), status_code

        logger.info(f"[TEST SCRAPER] Successfully scraped data for {airbnb_url} (Title: {scrape_results.get('title', 'N/A')})")
        return jsonify({'status': 'success', 'scrape_results': scrape_results}), 200
    except Exception as e:
        logger.error(f"[TEST SCRAPER] Unexpected exception during test for {airbnb_url}: {e}", exc_info=True)
        return jsonify({'error': f'An unexpected error occurred during scraper test: {str(e)}', 'status': 'error'}), 500

@underwriting_bp.route('/health', methods=['GET'])
def health_check():
    """Provides a health check for the underwriting service."""
    return jsonify({
        'status': 'healthy',
        'service': 'airbnb-underwriter-underwriting-blueprint', # More specific service name
        'version': '1.0.1'
    }), 200

@underwriting_bp.route('/test-calculator', methods=['POST'])
def test_calculator():
    """
    Tests the financial calculator with mock subject property, comparables, and financial inputs.
    Accepts a JSON body with 'mock_subject', 'mock_comparables', and 'financial_inputs'.
    If these are not provided, internal defaults are used for testing.

    Returns:
        JSON response with calculation results or an error message.
        Success (200): {'status': 'success', 'test_results': {...}}
        Error (400, 500): {'error': 'Error message', 'status': 'error'}
    """
    try:
        payload = request.get_json()
        if not payload: # Allow empty payload to use defaults
            logger.info("[TEST CALCULATOR] Empty payload, using default mock data.")
            payload = {}

        # Default mock data if not provided in payload
        mock_subject = payload.get('mock_subject', {
            'listing_url': 'https://www.airbnb.com/rooms/default_test',
            'title': 'Default Test Property', 'price_per_night': 120, 'cleaning_fee': 60,
            'num_bedrooms': 2, 'num_bathrooms': 1, 'num_reviews': 20, 'average_rating': 4.2,
            'guest_capacity': 3,
        })
        mock_comps = payload.get('mock_comparables', [
            {'price_per_night': 110, 'num_bedrooms': 2, 'num_reviews': 10, 'cleaning_fee': 50},
            {'price_per_night': 130, 'num_bedrooms': 2, 'num_reviews': 30, 'cleaning_fee': 70}
        ])
        financial_inputs = payload.get('financial_inputs', {})

        logger.info("[TEST CALCULATOR] Calculating with provided or default mock data.")
        results = calculate_underwriting(mock_subject, mock_comps, financial_inputs)

        return jsonify({'status': 'success', 'test_results': results}), 200
    except Exception as e:
        logger.error(f"[TEST CALCULATOR] Error: {e}", exc_info=True)
        return jsonify({'error': f'Calculator test failed: {str(e)}', 'status': 'error'}), 500

@underwriting_bp.route('/documentation', methods=['GET'])
def api_documentation():
    """Provides API documentation for the underwriting service."""
    # This could be expanded or point to a more formal documentation (e.g., Swagger UI).
    docs = {
        'service': 'Airbnb Underwriting Tool API',
        'version': '1.0.1',
        'description': 'Provides endpoints to analyze Airbnb property investment potential by scraping listing data, finding comparables, and performing financial calculations.',
        'endpoints': {
            '/api/underwriting/analyze': {
                'method': 'POST',
                'description': 'Main endpoint to analyze an Airbnb property. Scrapes property details, finds comparables, and runs financial underwriting.',
                'request_body_schema': {
                    'airbnb_url': 'string (required) - The full URL of the Airbnb listing.',
                    'num_comparables': 'integer (optional) - Target number of comparable listings to find (default: 5).',
                    'financial_inputs': 'object (optional) - Dictionary of financial parameters (see calculator.FinancialInputs for structure).'
                },
                'response_success (200)': 'JSON object with "status": "success", "subject_property", "comparable_properties", "underwriting_analysis", and "analysis_timestamp".',
                'response_error': 'JSON object with "status": "error" and "error" message (HTTP 400, 500, 502).'
            },
            '/api/underwriting/test-scraper': {
                'method': 'GET, POST',
                'description': 'Tests the scraper for a single Airbnb URL. Use GET with "airbnb_url" query parameter or POST with JSON/form body.',
                'request_parameters': 'airbnb_url (string, required)',
                'response_success (200)': 'JSON object with "status": "success" and "scrape_results".',
                'response_error': 'JSON object with "status": "error" and "error" message (HTTP 400, 500, 502).'
            },
            '/api/underwriting/test-calculator': {
                'method': 'POST',
                'description': 'Tests the financial calculator using mock data. Allows providing custom mock data in the JSON body.',
                'request_body_schema': {
                    'mock_subject': 'object (optional) - Mock data for the subject property.',
                    'mock_comparables': 'list (optional) - List of mock comparable properties.',
                    'financial_inputs': 'object (optional) - Financial parameters.'
                },
                'response_success (200)': 'JSON object with "status": "success" and "test_results".',
                'response_error': 'JSON object with "status": "error" and "error" message (HTTP 400, 500).'
            },
            '/api/underwriting/health': {
                'method': 'GET',
                'description': 'Health check for the underwriting blueprint.'
            },
            '/api/underwriting/documentation': {
                'method': 'GET',
                'description': 'This API documentation.'
            }
        }
    }
    return jsonify(docs), 200

logger.info("Underwriting blueprint routes configured and docstrings updated.")
