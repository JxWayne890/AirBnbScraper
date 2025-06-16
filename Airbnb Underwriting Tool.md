# Airbnb Underwriting Tool

A Python-based backend system for analyzing Airbnb investment properties. This tool scrapes Airbnb listings, finds comparable properties, and performs comprehensive financial underwriting calculations.

## Features

- **Airbnb Scraping**: Extracts property data from Airbnb listings including price, amenities, reviews, and location
- **Comparable Analysis**: Finds and analyzes 5-10 similar properties in the area
- **Financial Modeling**: Calculates best case, average case, and worst case revenue scenarios
- **Investment Metrics**: Computes ROI, payback period, cash flow, cap rate, and debt service coverage ratio
- **REST API**: JSON-based HTTP API for easy integration

## API Endpoints

### Main Analysis Endpoint
```
POST /api/underwriting/analyze
```

**Request Body:**
```json
{
  "airbnb_url": "https://www.airbnb.com/rooms/123456",
  "financial_inputs": {
    "purchase_price": 500000,
    "down_payment_percent": 25,
    "loan_interest_rate": 6.0,
    "closing_costs": 12000,
    "renovation_costs": 20000,
    "furniture_costs": 15000,
    "property_management_percent": 10,
    "average_stay_length": 3.0,
    "vacancy_rate": 0.15
  }
}
```

**Response:**
```json
{
  "status": "success",
  "subject_property": {
    "url": "...",
    "title": "...",
    "price_per_night": 150,
    "bedrooms": 2,
    "bathrooms": 1.5,
    "review_count": 45,
    "rating": 4.8
  },
  "comparable_properties": [...],
  "underwriting_analysis": {
    "investment_summary": {
      "total_investment": 140000,
      "down_payment": 125000,
      "loan_amount": 375000,
      "monthly_mortgage_payment": 2500
    },
    "revenue_scenarios": {
      "best_case": {
        "annual_revenue": 65000,
        "monthly_revenue": 5416,
        "occupancy_rate": 0.85,
        "adr": 165
      },
      "average_case": {...},
      "worst_case": {...}
    },
    "cash_flow_analysis": {
      "best_case": {
        "monthly_cash_flow": 1200,
        "annual_cash_flow": 14400
      },
      "average_case": {...},
      "worst_case": {...}
    },
    "roi_analysis": {
      "best_case_roi_percent": 15.2,
      "average_case_roi_percent": 8.5,
      "worst_case_roi_percent": -2.1,
      "best_case_payback_years": 6.6,
      "average_case_payback_years": 11.8,
      "worst_case_payback_years": "Infinity"
    },
    "additional_metrics": {
      "cap_rate_percent": 7.2,
      "cash_on_cash_return_percent": 10.3,
      "debt_service_coverage_ratio": 1.25
    },
    "assumptions": {...}
  }
}
```

### Other Endpoints

- `GET /health` - Health check
- `GET /api/underwriting/health` - Service health check
- `GET /api/underwriting/documentation` - Full API documentation
- `POST /api/underwriting/test-calculator` - Test calculator with mock data
- `POST /api/underwriting/test-scraper` - Test scraper functionality

## Local Development

1. **Clone and Setup**
   ```bash
   git clone <repository>
   cd airbnb-underwriter
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run Locally**
   ```bash
   python app.py
   ```
   
   The API will be available at `http://localhost:5000`

3. **Test the API**
   ```bash
   # Health check
   curl http://localhost:5000/health
   
   # Test calculator
   curl -X POST http://localhost:5000/api/underwriting/test-calculator \
     -H "Content-Type: application/json" \
     -d '{"financial_inputs": {"purchase_price": 400000}}'
   ```

## Deployment on Render

1. **Connect Repository**
   - Create a new Web Service on Render
   - Connect your GitHub repository

2. **Configuration**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3.11+

3. **Environment Variables** (Optional)
   - `PORT`: Automatically set by Render
   - Add any custom configuration variables as needed

## Financial Calculations

### Revenue Scenarios
- **Best Case**: 85% occupancy, 110% of market ADR
- **Average Case**: Market occupancy with vacancy rate applied
- **Worst Case**: 70% of average occupancy, 85% of market ADR

### Key Metrics
- **ROI**: (Annual Cash Flow / Total Investment) × 100
- **Payback Period**: Total Investment / Annual Cash Flow
- **Cap Rate**: Net Operating Income / Purchase Price
- **Cash-on-Cash Return**: Annual Cash Flow / Cash Invested
- **DSCR**: Net Operating Income / Annual Debt Service

### Assumptions
- Average stay length: 3 days
- Property management fee: 10% of revenue
- Vacancy rate: 15%
- Annual expense growth: 3%
- Annual revenue growth: 2%

## Dependencies

- Flask 2.3.3 - Web framework
- BeautifulSoup4 - Web scraping
- Requests - HTTP client
- Pandas/Numpy - Data analysis
- Gunicorn - WSGI server
- Flask-CORS - Cross-origin requests

## Project Structure

```
airbnb-underwriter/
├── app.py                 # Deployment entry point
├── Procfile              # Render deployment config
├── requirements.txt      # Python dependencies
├── src/
│   ├── main.py          # Flask application
│   ├── scraper.py       # Airbnb scraping logic
│   ├── calculator.py    # Financial calculations
│   └── routes/
│       └── underwriting.py  # API routes
└── venv/                # Virtual environment
```

## Error Handling

The API includes comprehensive error handling:
- Invalid URLs return 400 with error message
- Scraping failures return 500 with details
- Calculation errors are logged and return appropriate responses
- All endpoints return JSON with status indicators

## Rate Limiting

The scraper includes built-in delays to respect Airbnb's servers:
- Random delays between requests (1-3 seconds)
- User-Agent rotation
- Graceful error handling for blocked requests

## Support

For issues or questions:
1. Check the `/api/underwriting/documentation` endpoint
2. Test individual components with test endpoints
3. Review logs for detailed error information

