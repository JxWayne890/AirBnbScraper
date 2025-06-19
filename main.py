"""
Main Flask application file for the Airbnb Underwriting Tool.
Initializes the Flask app, registers blueprints, defines root and health endpoints,
and includes error handlers.
"""
import os
import sys
# DON'T CHANGE THIS !!! Ensures that modules in the project root can be found.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from flask import Flask, jsonify
from flask_cors import CORS
from underwriting import underwriting_bp
import logging

# Configure basic logging for the application.
# This should ideally be configured once. If other modules also call basicConfig,
# it might lead to unexpected behavior or multiple handlers.
# Consider a more centralized logging configuration for complex applications.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Secret key for session management and other security features (though not heavily used in this stateless API).
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'airbnb-underwriter-default-secret-key-202407')

# Enable Cross-Origin Resource Sharing (CORS) for all routes and all origins ("*").
# For production, specify allowed origins instead of "*" for better security.
CORS(app, origins="*")

# Register the underwriting blueprint, which contains all core API logic.
app.register_blueprint(underwriting_bp, url_prefix='/api/underwriting')

@app.route('/')
def home():
    """
    Root endpoint providing basic service information and a list of available API groups.

    Returns:
        JSON response with service details and status.
    """
    return jsonify({
        'service': 'Airbnb Underwriting Tool API',
        'version': '1.0.1', # Consistent versioning
        'description': 'API for analyzing Airbnb investment properties.',
        'documentation': '/api/underwriting/documentation', # Point to main docs
        'status': 'running'
    })

@app.route('/health')
def health():
    """
    Global health check endpoint for the entire application.

    Returns:
        JSON response indicating the service is healthy.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'airbnb-underwriter-main-app' # Differentiate from blueprint health
    })

@app.errorhandler(404)
def not_found(error):
    """
    Custom error handler for 404 Not Found errors.

    Args:
        error: The error object.

    Returns:
        JSON response with a 404 error message and a list of potentially useful endpoints.
    """
    logger.warning(f"404 Not Found: {request.path} (Error: {error})")
    # Provide a more helpful list of top-level available endpoints
    available_main_endpoints = ['/', '/health', '/api/underwriting/*']
    return jsonify({
        'error': 'Resource not found at this URL.',
        'requested_path': request.path,
        'status': 'error',
        'hint': 'Check the URL or refer to the API documentation.',
        'available_top_level_routes': available_main_endpoints
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """
    Custom error handler for 500 Internal Server Errors.
    Logs the error and returns a generic error message to the client.

    Args:
        error: The error object.

    Returns:
        JSON response with a 500 error message.
    """
    logger.error(f"Internal Server Error: {error} at {request.path}", exc_info=True) # Log full traceback
    return jsonify({
        'error': 'An unexpected internal server error occurred. Please try again later.',
        'status': 'error'
    }), 500

if __name__ == '__main__':
    # This block runs the Flask development server.
    # For production, a more robust WSGI server like Gunicorn (used in Procfile) should be used.
    logger.info("Starting Airbnb Underwriting Tool API in development mode...")
    # Use environment variable for port if available (e.g., for Render), default to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get("FLASK_DEBUG", "True").lower() == "true")
