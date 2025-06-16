import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import statistics
import logging

logger = logging.getLogger(__name__)

@dataclass
class FinancialInputs:
    """Input parameters for financial calculations"""
    purchase_price: float = 0.0
    down_payment_percent: float = 20.0
    loan_interest_rate: float = 6.5
    loan_term_years: int = 30
    closing_costs: float = 0.0
    renovation_costs: float = 0.0
    furniture_costs: float = 15000.0
    
    # Operating expenses (monthly)
    property_tax_monthly: float = 0.0
    insurance_monthly: float = 200.0
    hoa_fees_monthly: float = 0.0
    utilities_monthly: float = 150.0
    internet_monthly: float = 50.0
    maintenance_monthly: float = 200.0
    property_management_percent: float = 10.0
    
    # Other assumptions
    average_stay_length: float = 3.0  # days
    vacancy_rate: float = 0.15  # 15% vacancy
    annual_expense_growth: float = 0.03  # 3% annual growth
    annual_revenue_growth: float = 0.02  # 2% annual growth

@dataclass
class RevenueScenario:
    """Revenue scenario calculation results"""
    scenario_name: str
    annual_revenue: float
    monthly_revenue: float
    occupancy_rate: float
    adr: float  # Average Daily Rate
    cleaning_revenue: float
    total_nights_booked: int

@dataclass
class FinancialResults:
    """Complete financial analysis results"""
    # Input summary
    total_investment: float
    down_payment: float
    loan_amount: float
    monthly_mortgage_payment: float
    
    # Revenue scenarios
    best_case: RevenueScenario
    average_case: RevenueScenario
    worst_case: RevenueScenario
    
    # Expenses
    monthly_operating_expenses: float
    annual_operating_expenses: float
    
    # Cash flow analysis
    best_case_monthly_cash_flow: float
    average_case_monthly_cash_flow: float
    worst_case_monthly_cash_flow: float
    
    best_case_annual_cash_flow: float
    average_case_annual_cash_flow: float
    worst_case_annual_cash_flow: float
    
    # ROI and payback
    best_case_roi: float
    average_case_roi: float
    worst_case_roi: float
    
    best_case_payback_years: float
    average_case_payback_years: float
    worst_case_payback_years: float
    
    # Additional metrics
    cap_rate: float
    cash_on_cash_return: float
    debt_service_coverage_ratio: float
    
    # Assumptions used
    assumptions: Dict

class AirbnbUnderwriter:
    """Main class for Airbnb investment underwriting calculations"""
    
    def __init__(self, financial_inputs: FinancialInputs = None):
        self.inputs = financial_inputs or FinancialInputs()
    
    def analyze_investment(self, subject_property: Dict, comparable_properties: List[Dict], 
                          custom_inputs: Dict = None) -> FinancialResults:
        """
        Perform complete financial analysis of an Airbnb investment
        
        Args:
            subject_property: Scraped data for the subject property
            comparable_properties: List of comparable properties
            custom_inputs: Custom financial inputs to override defaults
        
        Returns:
            FinancialResults object with complete analysis
        """
        
        # Update inputs with custom values if provided
        if custom_inputs:
            self._update_inputs(custom_inputs)
        
        # Estimate property value if not provided
        if self.inputs.purchase_price == 0:
            self.inputs.purchase_price = self._estimate_property_value(subject_property)
        
        # Calculate basic financial metrics
        loan_metrics = self._calculate_loan_metrics()
        
        # Analyze revenue scenarios based on comps
        revenue_scenarios = self._analyze_revenue_scenarios(subject_property, comparable_properties)
        
        # Calculate operating expenses
        monthly_expenses = self._calculate_monthly_expenses(revenue_scenarios['average_case'])
        annual_expenses = monthly_expenses * 12
        
        # Calculate cash flows
        cash_flows = self._calculate_cash_flows(revenue_scenarios, monthly_expenses, loan_metrics['monthly_payment'])
        
        # Calculate ROI and payback periods
        roi_metrics = self._calculate_roi_metrics(cash_flows, loan_metrics['total_investment'])
        
        # Calculate additional investment metrics
        additional_metrics = self._calculate_additional_metrics(
            revenue_scenarios['average_case'], 
            annual_expenses, 
            loan_metrics
        )
        
        # Compile assumptions
        assumptions = self._compile_assumptions()
        
        return FinancialResults(
            # Investment summary
            total_investment=loan_metrics['total_investment'],
            down_payment=loan_metrics['down_payment'],
            loan_amount=loan_metrics['loan_amount'],
            monthly_mortgage_payment=loan_metrics['monthly_payment'],
            
            # Revenue scenarios
            best_case=revenue_scenarios['best_case'],
            average_case=revenue_scenarios['average_case'],
            worst_case=revenue_scenarios['worst_case'],
            
            # Expenses
            monthly_operating_expenses=monthly_expenses,
            annual_operating_expenses=annual_expenses,
            
            # Cash flows
            best_case_monthly_cash_flow=cash_flows['best_case_monthly'],
            average_case_monthly_cash_flow=cash_flows['average_case_monthly'],
            worst_case_monthly_cash_flow=cash_flows['worst_case_monthly'],
            
            best_case_annual_cash_flow=cash_flows['best_case_annual'],
            average_case_annual_cash_flow=cash_flows['average_case_annual'],
            worst_case_annual_cash_flow=cash_flows['worst_case_annual'],
            
            # ROI and payback
            best_case_roi=roi_metrics['best_case_roi'],
            average_case_roi=roi_metrics['average_case_roi'],
            worst_case_roi=roi_metrics['worst_case_roi'],
            
            best_case_payback_years=roi_metrics['best_case_payback'],
            average_case_payback_years=roi_metrics['average_case_payback'],
            worst_case_payback_years=roi_metrics['worst_case_payback'],
            
            # Additional metrics
            cap_rate=additional_metrics['cap_rate'],
            cash_on_cash_return=additional_metrics['cash_on_cash_return'],
            debt_service_coverage_ratio=additional_metrics['dscr'],
            
            # Assumptions
            assumptions=assumptions
        )
    
    def _update_inputs(self, custom_inputs: Dict):
        """Update financial inputs with custom values"""
        for key, value in custom_inputs.items():
            if hasattr(self.inputs, key):
                setattr(self.inputs, key, value)
    
    def _estimate_property_value(self, subject_property: Dict) -> float:
        """Estimate property value based on listing data"""
        # Simple estimation based on price per night and market factors
        price_per_night = subject_property.get('price_per_night', 100)
        bedrooms = subject_property.get('bedrooms', 1)
        bathrooms = subject_property.get('bathrooms', 1)
        
        # Basic estimation formula (this would be more sophisticated in reality)
        base_value = price_per_night * 365 * 15  # 15x annual revenue multiple
        bedroom_multiplier = 1 + (bedrooms * 0.2)
        bathroom_multiplier = 1 + (bathrooms * 0.1)
        
        estimated_value = base_value * bedroom_multiplier * bathroom_multiplier
        
        # Cap at reasonable ranges
        estimated_value = max(100000, min(2000000, estimated_value))
        
        logger.info(f"Estimated property value: ${estimated_value:,.2f}")
        return estimated_value
    
    def _calculate_loan_metrics(self) -> Dict:
        """Calculate loan-related financial metrics"""
        down_payment = self.inputs.purchase_price * (self.inputs.down_payment_percent / 100)
        loan_amount = self.inputs.purchase_price - down_payment
        
        # Calculate monthly mortgage payment
        monthly_rate = self.inputs.loan_interest_rate / 100 / 12
        num_payments = self.inputs.loan_term_years * 12
        
        if monthly_rate > 0:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / \
                            ((1 + monthly_rate)**num_payments - 1)
        else:
            monthly_payment = loan_amount / num_payments
        
        total_investment = down_payment + self.inputs.closing_costs + \
                          self.inputs.renovation_costs + self.inputs.furniture_costs
        
        return {
            'down_payment': down_payment,
            'loan_amount': loan_amount,
            'monthly_payment': monthly_payment,
            'total_investment': total_investment
        }
    
    def _analyze_revenue_scenarios(self, subject_property: Dict, comparable_properties: List[Dict]) -> Dict:
        """Analyze revenue scenarios based on subject property and comps"""
        
        # Extract key metrics from subject property
        subject_adr = subject_property.get('price_per_night', 100)
        subject_cleaning_fee = subject_property.get('cleaning_fee', 50)
        
        # Analyze comparable properties
        comp_adrs = []
        comp_occupancies = []
        comp_cleaning_fees = []
        
        for comp in comparable_properties:
            comp_adrs.append(comp.get('price_per_night', subject_adr))
            comp_cleaning_fees.append(comp.get('cleaning_fee', subject_cleaning_fee))
            
            # Estimate occupancy from review count and availability
            review_count = comp.get('review_count', 0)
            availability = comp.get('availability_365', 300)
            
            # Estimate occupancy based on review frequency
            if review_count > 0:
                # Assume 1 review per 3 stays on average
                estimated_stays_per_year = review_count * 3
                estimated_nights_per_year = estimated_stays_per_year * self.inputs.average_stay_length
                occupancy = min(0.9, estimated_nights_per_year / 365)
            else:
                occupancy = 0.5  # Default for properties with no reviews
            
            comp_occupancies.append(occupancy)
        
        # Calculate scenario metrics
        if comp_adrs:
            avg_market_adr = statistics.mean(comp_adrs)
            avg_market_occupancy = statistics.mean(comp_occupancies) if comp_occupancies else 0.65
            avg_cleaning_fee = statistics.mean(comp_cleaning_fees) if comp_cleaning_fees else subject_cleaning_fee
        else:
            avg_market_adr = subject_adr
            avg_market_occupancy = 0.65
            avg_cleaning_fee = subject_cleaning_fee
        
        # Define scenarios
        scenarios = {
            'best_case': {
                'adr': max(subject_adr, avg_market_adr * 1.1),
                'occupancy': min(0.85, avg_market_occupancy * 1.2),
                'name': 'Best Case'
            },
            'average_case': {
                'adr': avg_market_adr,
                'occupancy': avg_market_occupancy * (1 - self.inputs.vacancy_rate),
                'name': 'Average Case'
            },
            'worst_case': {
                'adr': min(subject_adr, avg_market_adr * 0.85),
                'occupancy': max(0.3, avg_market_occupancy * 0.7),
                'name': 'Worst Case'
            }
        }
        
        # Calculate revenue for each scenario
        scenario_results = {}
        
        for scenario_key, scenario_data in scenarios.items():
            nights_booked = int(365 * scenario_data['occupancy'])
            stays_per_year = nights_booked / self.inputs.average_stay_length
            
            room_revenue = nights_booked * scenario_data['adr']
            cleaning_revenue = stays_per_year * avg_cleaning_fee
            annual_revenue = room_revenue + cleaning_revenue
            
            scenario_results[scenario_key] = RevenueScenario(
                scenario_name=scenario_data['name'],
                annual_revenue=annual_revenue,
                monthly_revenue=annual_revenue / 12,
                occupancy_rate=scenario_data['occupancy'],
                adr=scenario_data['adr'],
                cleaning_revenue=cleaning_revenue,
                total_nights_booked=nights_booked
            )
        
        return scenario_results
    
    def _calculate_monthly_expenses(self, average_scenario: RevenueScenario) -> float:
        """Calculate total monthly operating expenses"""
        
        # Property tax (estimate if not provided)
        if self.inputs.property_tax_monthly == 0:
            # Estimate at 1.2% annually
            self.inputs.property_tax_monthly = (self.inputs.purchase_price * 0.012) / 12
        
        # Property management fee
        property_mgmt_fee = average_scenario.monthly_revenue * (self.inputs.property_management_percent / 100)
        
        # Total monthly expenses
        total_monthly = (
            self.inputs.property_tax_monthly +
            self.inputs.insurance_monthly +
            self.inputs.hoa_fees_monthly +
            self.inputs.utilities_monthly +
            self.inputs.internet_monthly +
            self.inputs.maintenance_monthly +
            property_mgmt_fee
        )
        
        return total_monthly
    
    def _calculate_cash_flows(self, revenue_scenarios: Dict, monthly_expenses: float, monthly_mortgage: float) -> Dict:
        """Calculate cash flows for all scenarios"""
        
        cash_flows = {}
        
        for scenario_key, scenario in revenue_scenarios.items():
            monthly_cash_flow = scenario.monthly_revenue - monthly_expenses - monthly_mortgage
            annual_cash_flow = monthly_cash_flow * 12
            
            cash_flows[f'{scenario_key}_monthly'] = monthly_cash_flow
            cash_flows[f'{scenario_key}_annual'] = annual_cash_flow
        
        return cash_flows
    
    def _calculate_roi_metrics(self, cash_flows: Dict, total_investment: float) -> Dict:
        """Calculate ROI and payback period metrics"""
        
        roi_metrics = {}
        
        scenarios = ['best_case', 'average_case', 'worst_case']
        
        for scenario in scenarios:
            annual_cash_flow = cash_flows[f'{scenario}_annual']
            
            # ROI calculation
            if total_investment > 0:
                roi = (annual_cash_flow / total_investment) * 100
            else:
                roi = 0
            
            # Payback period calculation
            if annual_cash_flow > 0:
                payback_years = total_investment / annual_cash_flow
            else:
                payback_years = float('inf')
            
            roi_metrics[f'{scenario}_roi'] = roi
            roi_metrics[f'{scenario}_payback'] = payback_years
        
        return roi_metrics
    
    def _calculate_additional_metrics(self, average_scenario: RevenueScenario, annual_expenses: float, loan_metrics: Dict) -> Dict:
        """Calculate additional investment metrics"""
        
        # Cap rate (if purchased all cash)
        net_operating_income = average_scenario.annual_revenue - annual_expenses
        cap_rate = (net_operating_income / self.inputs.purchase_price) * 100 if self.inputs.purchase_price > 0 else 0
        
        # Cash-on-cash return
        annual_cash_flow = net_operating_income - (loan_metrics['monthly_payment'] * 12)
        cash_on_cash_return = (annual_cash_flow / loan_metrics['total_investment']) * 100 if loan_metrics['total_investment'] > 0 else 0
        
        # Debt Service Coverage Ratio
        annual_debt_service = loan_metrics['monthly_payment'] * 12
        dscr = net_operating_income / annual_debt_service if annual_debt_service > 0 else 0
        
        return {
            'cap_rate': cap_rate,
            'cash_on_cash_return': cash_on_cash_return,
            'dscr': dscr
        }
    
    def _compile_assumptions(self) -> Dict:
        """Compile all assumptions used in calculations"""
        return {
            'purchase_price': self.inputs.purchase_price,
            'down_payment_percent': self.inputs.down_payment_percent,
            'loan_interest_rate': self.inputs.loan_interest_rate,
            'loan_term_years': self.inputs.loan_term_years,
            'average_stay_length_days': self.inputs.average_stay_length,
            'vacancy_rate': self.inputs.vacancy_rate,
            'property_management_percent': self.inputs.property_management_percent,
            'annual_expense_growth': self.inputs.annual_expense_growth,
            'annual_revenue_growth': self.inputs.annual_revenue_growth,
            'furniture_costs': self.inputs.furniture_costs,
            'renovation_costs': self.inputs.renovation_costs,
            'closing_costs': self.inputs.closing_costs,
            'monthly_insurance': self.inputs.insurance_monthly,
            'monthly_utilities': self.inputs.utilities_monthly,
            'monthly_internet': self.inputs.internet_monthly,
            'monthly_maintenance': self.inputs.maintenance_monthly
        }

def calculate_underwriting(subject_property: Dict, comparable_properties: List[Dict], 
                         financial_inputs: Dict = None) -> Dict:
    """
    Main function to calculate Airbnb investment underwriting
    
    Args:
        subject_property: Scraped data for the subject property
        comparable_properties: List of comparable properties
        financial_inputs: Custom financial inputs
    
    Returns:
        Dictionary with complete underwriting analysis
    """
    
    # Create financial inputs object
    inputs = FinancialInputs()
    
    # Create underwriter instance
    underwriter = AirbnbUnderwriter(inputs)
    
    # Perform analysis
    results = underwriter.analyze_investment(subject_property, comparable_properties, financial_inputs)
    
    # Convert results to dictionary for JSON serialization
    return {
        'investment_summary': {
            'total_investment': results.total_investment,
            'down_payment': results.down_payment,
            'loan_amount': results.loan_amount,
            'monthly_mortgage_payment': results.monthly_mortgage_payment
        },
        'revenue_scenarios': {
            'best_case': {
                'scenario_name': results.best_case.scenario_name,
                'annual_revenue': results.best_case.annual_revenue,
                'monthly_revenue': results.best_case.monthly_revenue,
                'occupancy_rate': results.best_case.occupancy_rate,
                'adr': results.best_case.adr,
                'cleaning_revenue': results.best_case.cleaning_revenue,
                'total_nights_booked': results.best_case.total_nights_booked
            },
            'average_case': {
                'scenario_name': results.average_case.scenario_name,
                'annual_revenue': results.average_case.annual_revenue,
                'monthly_revenue': results.average_case.monthly_revenue,
                'occupancy_rate': results.average_case.occupancy_rate,
                'adr': results.average_case.adr,
                'cleaning_revenue': results.average_case.cleaning_revenue,
                'total_nights_booked': results.average_case.total_nights_booked
            },
            'worst_case': {
                'scenario_name': results.worst_case.scenario_name,
                'annual_revenue': results.worst_case.annual_revenue,
                'monthly_revenue': results.worst_case.monthly_revenue,
                'occupancy_rate': results.worst_case.occupancy_rate,
                'adr': results.worst_case.adr,
                'cleaning_revenue': results.worst_case.cleaning_revenue,
                'total_nights_booked': results.worst_case.total_nights_booked
            }
        },
        'expenses': {
            'monthly_operating_expenses': results.monthly_operating_expenses,
            'annual_operating_expenses': results.annual_operating_expenses
        },
        'cash_flow_analysis': {
            'best_case': {
                'monthly_cash_flow': results.best_case_monthly_cash_flow,
                'annual_cash_flow': results.best_case_annual_cash_flow
            },
            'average_case': {
                'monthly_cash_flow': results.average_case_monthly_cash_flow,
                'annual_cash_flow': results.average_case_annual_cash_flow
            },
            'worst_case': {
                'monthly_cash_flow': results.worst_case_monthly_cash_flow,
                'annual_cash_flow': results.worst_case_annual_cash_flow
            }
        },
        'roi_analysis': {
            'best_case_roi_percent': results.best_case_roi,
            'average_case_roi_percent': results.average_case_roi,
            'worst_case_roi_percent': results.worst_case_roi,
            'best_case_payback_years': results.best_case_payback_years,
            'average_case_payback_years': results.average_case_payback_years,
            'worst_case_payback_years': results.worst_case_payback_years
        },
        'additional_metrics': {
            'cap_rate_percent': results.cap_rate,
            'cash_on_cash_return_percent': results.cash_on_cash_return,
            'debt_service_coverage_ratio': results.debt_service_coverage_ratio
        },
        'assumptions': results.assumptions
    }

