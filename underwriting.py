from flask import Blueprint, request, jsonify
from src.scraper import scrape_airbnb_listing
from src.calculator import calculate_underwriting
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint for underwriting routes
underwriting_bp = Blueprint('underwriting', __name__)

@underwriting_bp.route('/analyze', methods=['POST'])
def analyze_property():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'status': 'error'
            }), 400

        airbnb_url = data.get('airbnb_url')
        if not airbnb_url:
            return jsonify({
                'error': 'airbnb_url is required',
                'status': 'error'
            }), 400

        if 'airbnb.com' not in airbnb_url:
            return jsonify({
                'error': 'Invalid Airbnb URL format',
                'status': 'error'
            }), 400

        financial_inputs = data.get('financial_inputs', {})

        logger.info(f"Starting analysis for URL: {airbnb_url}")
        logger.info("Scraping Airbnb listing and finding comparables...")
        scrape_results = scrape_airbnb_listing(airbnb_url)

        if 'error' in scrape_results:
            return jsonify({
                'error': f'Failed to scrape listing: {scrape_results["error"]}',
                'status': 'error'
            }), 500

        subject_property = scrape_results['subject_property']
        comparable_properties = scrape_results['comparable_properties']

        logger.info(f"Successfully scraped subject property and {len(comparable_properties)} comparables")

        logger.info("Performing financial underwriting analysis...")
        underwriting_results = calculate_underwriting(
            subject_property, 
            comparable_properties, 
            financial_inputs
        )

        response = {
            'status': 'success',
            'analysis_timestamp': scrape_results.get('scrape_timestamp'),
            'subject_property': subject_property,
            'comparable_properties': comparable_properties,
            'underwriting_analysis': underwriting_results
        }

        logger.info("Analysis completed successfully")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in analyze_property: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'status': 'error'
        }), 500

@underwriting_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'airbnb-underwriter',
        'version': '1.0.0'
    }), 200

@underwriting_bp.route('/test-scraper', methods=['POST'])
def test_scraper():
    try:
        data = request.get_json()
        airbnb_url = data.get('airbnb_url')

        if not airbnb_url:
            return jsonify({
                'error': 'airbnb_url is required',
                'status': 'error'
            }), 400

        logger.info(f"[TEST SCRAPER] Real scrape for: {airbnb_url}")

        scrape_results = scrape_airbnb_listing(airbnb_url, allow_mock=False)

        if not scrape_results or "subject_property" not in scrape_results:
            return jsonify({
                'error': 'No valid scrape results returned.',
                'status': 'error'
            }), 500

        return jsonify({
            'status': 'success',
            'scrape_results': scrape_results
        }), 200

    except Exception as e:
        logger.error(f"Error in test_scraper: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f'Scraper test failed: {str(e)}',
            'status': 'error'
        }), 500

@underwriting_bp.route('/test-calculator', methods=['POST'])
def test_calculator():
    try:
        data = request.get_json()

        mock_subject = {
            'url': 'https://www.airbnb.com/rooms/test',
            'title': 'Test Property',
            'price_per_night': 150,
            'cleaning_fee': 75,
            'bedrooms': 2,
            'bathrooms': 1.5,
            'review_count': 50,
            'rating': 4.8
        }

        mock_comps = [
            {
                'url': 'https://www.airbnb.com/rooms/comp1',
                'price_per_night': 140,
                'cleaning_fee': 70,
                'bedrooms': 2,
                'bathrooms': 1,
                'review_count': 30,
                'rating': 4.6
            },
            {
                'url': 'https://www.airbnb.com/rooms/comp2',
                'price_per_night': 160,
                'cleaning_fee': 80,
                'bedrooms': 2,
                'bathrooms': 2,
                'review_count': 75,
                'rating': 4.9
            }
        ]

        financial_inputs = data.get('financial_inputs', {})

        logger.info("Testing calculator with mock data")

        results = calculate_underwriting(mock_subject, mock_comps, financial_inputs)

        return jsonify({
            'status': 'success',
            'test_results': results
        }), 200

    except Exception as e:
        logger.error(f"Error in test_calculator: {str(e)}")
        return jsonify({
            'error': f'Calculator test failed: {str(e)}',
            'status': 'error'
        }), 500

@underwriting_bp.route('/documentation', methods=['GET'])
def api_documentation():
    docs = {
        'service': 'Airbnb Underwriting Tool',
        'version': '1.0.0',
        'description': 'API for analyzing Airbnb investment properties',
        'endpoints': {
            'POST /api/underwriting/analyze': {
                'description': 'Analyze an Airbnb property for investment potential',
                'required_parameters': {
                    'airbnb_url': 'string - Valid Airbnb listing URL'
                },
                'optional_parameters': {
                    'financial_inputs': {
                        'purchase_price': 'number',
                        'down_payment_percent': 'number',
                        'loan_interest_rate': 'number',
                        'loan_term_years': 'number',
                        'closing_costs': 'number',
                        'renovation_costs': 'number',
                        'furniture_costs': 'number',
                        'property_tax_monthly': 'number',
                        'insurance_monthly': 'number',
                        'hoa_fees_monthly': 'number',
                        'utilities_monthly': 'number',
                        'internet_monthly': 'number',
                        'maintenance_monthly': 'number',
                        'property_management_percent': 'number',
                        'average_stay_length': 'number',
                        'vacancy_rate': 'number'
                    }
                },
                'response': {
                    'status': 'string',
                    'subject_property': 'object',
                    'comparable_properties': 'array',
                    'underwriting_analysis': 'object'
                }
            },
            'GET /api/underwriting/health': {
                'description': 'Health check endpoint'
            },
            'POST /api/underwriting/test-scraper': {
                'description': 'Test scraper functionality',
                'required_parameters': {
                    'airbnb_url': 'string - Valid Airbnb listing URL'
                }
            },
            'POST /api/underwriting/test-calculator': {
                'description': 'Test calculator functionality',
                'optional_parameters': {
                    'financial_inputs': 'object'
                }
            }
        }
    }

    return jsonify(docs), 200
