import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify
from flask_cors import CORS
from src.routes.underwriting import underwriting_bp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'airbnb-underwriter-secret-key-2024'

# Enable CORS for all routes
CORS(app, origins="*")

# Register underwriting blueprint
app.register_blueprint(underwriting_bp, url_prefix='/api/underwriting')

@app.route('/')
def home():
    """Root endpoint with service information"""
    return jsonify({
        'service': 'Airbnb Underwriting Tool',
        'version': '1.0.0',
        'description': 'API for analyzing Airbnb investment properties',
        'endpoints': {
            'documentation': '/api/underwriting/documentation',
            'health_check': '/api/underwriting/health',
            'analyze_property': '/api/underwriting/analyze',
            'test_scraper': '/api/underwriting/test-scraper',
            'test_calculator': '/api/underwriting/test-calculator'
        },
        'status': 'running'
    })

@app.route('/health')
def health():
    """Global health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'airbnb-underwriter'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error',
        'available_endpoints': [
            '/',
            '/health',
            '/api/underwriting/documentation',
            '/api/underwriting/health',
            '/api/underwriting/analyze',
            '/api/underwriting/test-scraper',
            '/api/underwriting/test-calculator'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500

if __name__ == '__main__':
    logger.info("Starting Airbnb Underwriting Tool API...")
    app.run(host='0.0.0.0', port=5000, debug=True)
