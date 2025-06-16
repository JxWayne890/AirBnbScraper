import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from src.main import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

