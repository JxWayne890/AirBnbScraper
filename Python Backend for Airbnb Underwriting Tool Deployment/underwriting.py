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
    """
    Main endpoint for Airbnb property underwriting analysis
    
    Expected JSON payload:
    {
        "airbnb_url": "https://www.airbnb.com/rooms/123456",
        "financial_inputs": {  // Optional
            "purchase_price": 500000,
            "down_payment_percent": 20,
            "loan_interest_rate": 6.5,
            "closing_costs": 10000,
            "renovation_costs": 15000,
            "furniture_costs": 20000,
            // ... other financial parameters
        }
    }
    """
    try:
        # Get request data
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
        
        # Validate URL format
        if 'airbnb.com' not in airbnb_url:
            return jsonify({
                'error': 'Invalid Airbnb URL format',
                'status': 'error'
            }), 400
        
        financial_inputs = data.get('financial_inputs', {})
        
        logger.info(f"Starting analysis for URL: {airbnb_url}")
        
        # Step 1: Scrape the listing and find comparables
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
        
        # Step 2: Perform financial analysis
        logger.info("Performing financial underwriting analysis...")
        underwriting_results = calculate_underwriting(
            subject_property, 
            comparable_properties, 
            financial_inputs
        )
        
        # Step 3: Compile complete response
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
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'airbnb-underwriter',
        'version': '1.0.0'
    }), 200

@underwriting_bp.route('/test-scraper', methods=['POST'])
def test_scraper():
    """Test endpoint for scraper functionality"""
    try:
        data = request.get_json()
        airbnb_url = data.get('airbnb_url')
        
        if not airbnb_url:
            return jsonify({
                'error': 'airbnb_url is required',
                'status': 'error'
            }), 400
        
        logger.info(f"Testing scraper for URL: {airbnb_url}")
        
        scrape_results = scrape_airbnb_listing(airbnb_url)
        
        return jsonify({
            'status': 'success',
            'scrape_results': scrape_results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in test_scraper: {str(e)}")
        return jsonify({
            'error': f'Scraper test failed: {str(e)}',
            'status': 'error'
        }), 500

@underwriting_bp.route('/test-calculator', methods=['POST'])
def test_calculator():
    """Test endpoint for calculator functionality"""
    try:
        data = request.get_json()
        
        # Mock subject property data for testing
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
        
        # Mock comparable properties
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
    """API documentation endpoint"""
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
                        'purchase_price': 'number - Property purchase price',
                        'down_payment_percent': 'number - Down payment percentage (default: 20)',
                        'loan_interest_rate': 'number - Loan interest rate (default: 6.5)',
                        'loan_term_years': 'number - Loan term in years (default: 30)',
                        'closing_costs': 'number - Closing costs (default: 0)',
                        'renovation_costs': 'number - Renovation costs (default: 0)',
                        'furniture_costs': 'number - Furniture costs (default: 15000)',
                        'property_tax_monthly': 'number - Monthly property tax',
                        'insurance_monthly': 'number - Monthly insurance (default: 200)',
                        'hoa_fees_monthly': 'number - Monthly HOA fees (default: 0)',
                        'utilities_monthly': 'number - Monthly utilities (default: 150)',
                        'internet_monthly': 'number - Monthly internet (default: 50)',
                        'maintenance_monthly': 'number - Monthly maintenance (default: 200)',
                        'property_management_percent': 'number - Property management fee % (default: 10)',
                        'average_stay_length': 'number - Average stay length in days (default: 3)',
                        'vacancy_rate': 'number - Vacancy rate (default: 0.15)'
                    }
                },
                'response': {
                    'status': 'string - success or error',
                    'subject_property': 'object - Scraped property data',
                    'comparable_properties': 'array - Comparable properties data',
                    'underwriting_analysis': 'object - Complete financial analysis'
                }
            },
            'GET /api/underwriting/health': {
                'description': 'Health check endpoint',
                'response': {
                    'status': 'string - healthy',
                    'service': 'string - service name',
                    'version': 'string - service version'
                }
            },
            'POST /api/underwriting/test-scraper': {
                'description': 'Test scraper functionality',
                'required_parameters': {
                    'airbnb_url': 'string - Valid Airbnb listing URL'
                }
            },
            'POST /api/underwriting/test-calculator': {
                'description': 'Test calculator functionality with mock data',
                'optional_parameters': {
                    'financial_inputs': 'object - Financial input parameters'
                }
            }
        },
        'example_request': {
            'url': '/api/underwriting/analyze',
            'method': 'POST',
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': {
                'airbnb_url': 'https://www.airbnb.com/rooms/123456',
                'financial_inputs': {
                    'purchase_price': 500000,
                    'down_payment_percent': 25,
                    'loan_interest_rate': 6.0,
                    'closing_costs': 12000,
                    'renovation_costs': 20000
                }
            }
        }
    }
    
    return jsonify(docs), 200

