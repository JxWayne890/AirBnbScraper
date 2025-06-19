import unittest
from calculator import calculate_underwriting, FinancialInputs # Assuming FinancialInputs might be useful for setup

# Sample data mimicking scraper output (aligned with scraper.py)
SAMPLE_SUBJECT_PROPERTY = {
    "listing_url": "https://www.airbnb.com/rooms/123",
    "listing_id": "123",
    "title": "Test Subject Property",
    "price_per_night": 150.0,
    "currency": "USD",
    "description": "A nice place.",
    "guest_capacity": 4,
    "num_bedrooms": 2,
    "num_bathrooms": 1.5,
    "average_rating": 4.5,
    "num_reviews": 100,
    "amenities": ["Wifi", "Kitchen"],
    "host_type": "Superhost",
    "address_neighborhood": "Test City, CA",
    "cleaning_fee": 60.0,
    "service_fee": 20.0 # Scraper might provide this, calculator might not use it yet
}

SAMPLE_COMPARABLE_PROPERTIES = [
    {
        "listing_url": "https://www.airbnb.com/rooms/comp1",
        "listing_id": "comp1",
        "price_per_night": 140.0,
        "num_bedrooms": 2,
        "num_bathrooms": 1.0,
        "num_reviews": 80,
        "average_rating": 4.4,
        "cleaning_fee": 50.0,
        "availability_365": 300 # Calculator uses this with a default if not present
    },
    {
        "listing_url": "https://www.airbnb.com/rooms/comp2",
        "listing_id": "comp2",
        "price_per_night": 160.0,
        "num_bedrooms": 2,
        "num_bathrooms": 2.0,
        "num_reviews": 120,
        "average_rating": 4.6,
        "cleaning_fee": 70.0,
        "availability_365": 320
    }
]

# Sample financial inputs, can be overridden in tests
SAMPLE_FINANCIAL_INPUTS = {
    "purchase_price": 300000.0,
    "down_payment_percent": 20.0,
    "loan_interest_rate": 6.0, # Using a slightly different rate for mortgage test
    "loan_term_years": 30,
    "closing_costs": 5000.0,
    "renovation_costs": 10000.0,
    "furniture_costs": 15000.0,
    "property_tax_monthly": 300.0, # (purchase_price * 0.012) / 12 = 300 if 1.2% of 300k
    "insurance_monthly": 100.0,
    "hoa_fees_monthly": 0.0,
    "utilities_monthly": 150.0,
    "internet_monthly": 60.0,
    "maintenance_monthly": 100.0,
    "property_management_percent": 10.0,
    "average_stay_length": 3.0,
    "vacancy_rate": 0.10 # 10%
}


class TestCalculator(unittest.TestCase):

    def test_calculate_underwriting_basic_case(self):
        results = calculate_underwriting(
            SAMPLE_SUBJECT_PROPERTY,
            SAMPLE_COMPARABLE_PROPERTIES,
            SAMPLE_FINANCIAL_INPUTS
        )
        self.assertIsNotNone(results)
        self.assertIn("investment_summary", results)
        self.assertIn("revenue_scenarios", results)
        self.assertIn("expenses", results)
        self.assertIn("cash_flow_analysis", results)
        self.assertIn("roi_analysis", results)
        self.assertIn("additional_metrics", results)
        self.assertIn("assumptions", results)

        # Check a few specific calculated values
        # Mortgage for 300k purchase, 20% down (240k loan), 30yr, 6% rate
        # Expected monthly mortgage: approx $1438.93
        # total_investment = down_payment (60k) + closing (5k) + renovation (10k) + furniture (15k) = 90k
        self.assertAlmostEqual(results["investment_summary"]["monthly_mortgage_payment"], 1438.93, delta=1)
        self.assertEqual(results["investment_summary"]["total_investment"], 90000.0)
        self.assertEqual(results["investment_summary"]["down_payment"], 60000.0)
        self.assertEqual(results["investment_summary"]["loan_amount"], 240000.0)


    def test_revenue_scenarios_ordering_and_content(self):
        results = calculate_underwriting(
            SAMPLE_SUBJECT_PROPERTY,
            SAMPLE_COMPARABLE_PROPERTIES,
            SAMPLE_FINANCIAL_INPUTS
        )
        revenue = results["revenue_scenarios"]
        self.assertIn("best_case", revenue)
        self.assertIn("average_case", revenue)
        self.assertIn("worst_case", revenue)

        # ADR for average should be mean of comps' ADRs if available
        # Comp ADRs: 140, 160. Mean = 150. Subject ADR = 150.
        # So, average ADR should be 150.
        self.assertAlmostEqual(revenue["average_case"]["adr"], 150.0, delta=1)

        # Best case ADR should be >= average, worst case ADR should be <= average
        self.assertGreaterEqual(revenue["best_case"]["adr"], revenue["average_case"]["adr"])
        self.assertLessEqual(revenue["worst_case"]["adr"], revenue["average_case"]["adr"])

        # Check that annual revenues are also ordered
        self.assertGreaterEqual(revenue["best_case"]["annual_revenue"], revenue["average_case"]["annual_revenue"])
        self.assertLessEqual(revenue["worst_case"]["annual_revenue"], revenue["average_case"]["annual_revenue"])

        # Ensure all revenue scenarios have necessary keys
        for scenario_name in ["best_case", "average_case", "worst_case"]:
            self.assertIn("annual_revenue", revenue[scenario_name])
            self.assertIn("monthly_revenue", revenue[scenario_name])
            self.assertIn("occupancy_rate", revenue[scenario_name])
            self.assertIn("adr", revenue[scenario_name])
            self.assertIn("cleaning_revenue", revenue[scenario_name])
            self.assertIn("total_nights_booked", revenue[scenario_name])

    def test_estimate_property_value_usage(self):
        # Test when purchase_price is not provided in financial_inputs
        inputs_no_price = SAMPLE_FINANCIAL_INPUTS.copy()
        inputs_no_price["purchase_price"] = 0 # Signal to estimate

        # Scraper provides num_bedrooms=2, num_bathrooms=1.5, price_per_night=150
        # Estimated value = (150 * 365 * 15) * (1 + 2*0.2) * (1 + 1.5*0.1)
        # = 821250 * 1.4 * 1.15 = 1320337.5
        # This is capped between 100k and 2M, so it's a valid estimate.

        results = calculate_underwriting(
            SAMPLE_SUBJECT_PROPERTY,
            SAMPLE_COMPARABLE_PROPERTIES,
            inputs_no_price
        )
        # Check that the estimated purchase price was used in assumptions
        self.assertAlmostEqual(results["assumptions"]["purchase_price"], 1320337.5, delta=1)
        # And that this affects loan amount, etc.
        # Down payment: 20% of 1320337.5 = 264067.5
        # Loan amount: 1320337.5 - 264067.5 = 1056270
        self.assertAlmostEqual(results["investment_summary"]["down_payment"], 264067.5, delta=1)
        self.assertAlmostEqual(results["investment_summary"]["loan_amount"], 1056270, delta=1)

    def test_zero_comparables(self):
        # Test how calculator handles having no comparable properties
        results = calculate_underwriting(
            SAMPLE_SUBJECT_PROPERTY,
            [], # Empty list of comparables
            SAMPLE_FINANCIAL_INPUTS
        )
        self.assertIsNotNone(results)
        # Average case ADR should fall back to subject property's ADR (150)
        self.assertAlmostEqual(results["revenue_scenarios"]["average_case"]["adr"], 150.0, delta=1)
        # Default occupancy for average case when no comps (0.65 * (1 - vacancy_rate 0.1)) = 0.585
        self.assertAlmostEqual(results["revenue_scenarios"]["average_case"]["occupancy_rate"], 0.65 * (1.0 - SAMPLE_FINANCIAL_INPUTS["vacancy_rate"]), delta=0.01)


    def test_negative_cash_flow(self):
        # Test with very high expenses to ensure cash flow can be negative
        high_expense_inputs = SAMPLE_FINANCIAL_INPUTS.copy()
        high_expense_inputs["maintenance_monthly"] = 5000 # Very high maintenance

        results = calculate_underwriting(
            SAMPLE_SUBJECT_PROPERTY,
            SAMPLE_COMPARABLE_PROPERTIES,
            high_expense_inputs
        )
        self.assertLess(results["cash_flow_analysis"]["average_case"]["annual_cash_flow"], 0)
        self.assertLess(results["roi_analysis"]["average_case_roi_percent"], 0)
        # Payback years should be infinity if cash flow is not positive
        self.assertEqual(results["roi_analysis"]["average_case_payback_years"], float('inf'))

    def test_zero_purchase_price_and_no_subject_property_for_estimation(self):
        # Test when purchase_price is 0 and subject_property is empty (cannot estimate)
        inputs_no_price = SAMPLE_FINANCIAL_INPUTS.copy()
        inputs_no_price["purchase_price"] = 0

        # The calculator's _estimate_property_value returns None, then it defaults to 250000
        results = calculate_underwriting(
            {}, # Empty subject property
            SAMPLE_COMPARABLE_PROPERTIES,
            inputs_no_price
        )
        self.assertEqual(results["assumptions"]["purchase_price"], 250000.0) # Default fallback
        # Down payment: 20% of 250k = 50k
        # Loan amount: 200k
        self.assertEqual(results["investment_summary"]["down_payment"], 50000.0)
        self.assertEqual(results["investment_summary"]["loan_amount"], 200000.0)


if __name__ == '__main__':
    unittest.main()
