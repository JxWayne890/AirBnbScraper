from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import statistics
import logging

logger = logging.getLogger(__name__)

@dataclass
class FinancialInputs:
    """
    Dataclass holding all financial input parameters for underwriting calculations.
    Default values are provided for many common assumptions.
    """
    purchase_price: float = 0.0
    down_payment_percent: float = 20.0  # Percentage (e.g., 20 for 20%)
    loan_interest_rate: float = 6.5    # Annual interest rate (e.g., 6.5 for 6.5%)
    loan_term_years: int = 30
    closing_costs: float = 0.0
    renovation_costs: float = 0.0
    furniture_costs: float = 15000.0
    
    # Operating expenses (monthly estimates)
    property_tax_monthly: float = 0.0  # Can be estimated if not provided
    insurance_monthly: float = 200.0
    hoa_fees_monthly: float = 0.0
    utilities_monthly: float = 150.0   # (e.g., electricity, water, gas)
    internet_monthly: float = 50.0
    maintenance_monthly: float = 200.0 # (e.g., repairs, upkeep fund)
    property_management_percent: float = 10.0 # Percentage of gross revenue

    # Other operational assumptions
    average_stay_length: float = 3.0  # Average number of days per booking
    vacancy_rate: float = 0.15        # e.g., 0.15 for 15% vacancy (time not booked)
    annual_expense_growth: float = 0.03 # Expected annual increase in operating expenses
    annual_revenue_growth: float = 0.02 # Expected annual increase in revenue (e.g., ADR increase)

@dataclass
class RevenueScenario:
    """
    Represents the calculated revenue metrics for a specific scenario (e.g., best, average, worst).
    """
    scenario_name: str
    annual_revenue: float
    monthly_revenue: float
    occupancy_rate: float # Effective occupancy after considering vacancy
    adr: float            # Average Daily Rate for this scenario
    cleaning_revenue: float
    total_nights_booked: int

@dataclass
class FinancialResults:
    """
    Consolidates all results from the financial underwriting analysis.
    Includes summaries of investment, revenue, expenses, cash flow, ROI, and key assumptions.
    """
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
    monthly_operating_expenses: float # Excluding mortgage
    annual_operating_expenses: float  # Excluding mortgage
    
    # Cash flow analysis (Net cash flow after all expenses including mortgage)
    best_case_monthly_cash_flow: float
    average_case_monthly_cash_flow: float
    worst_case_monthly_cash_flow: float
    
    best_case_annual_cash_flow: float
    average_case_annual_cash_flow: float
    worst_case_annual_cash_flow: float
    
    # ROI and payback
    best_case_roi: float  # Return on Investment (Annual Cash Flow / Total Investment)
    average_case_roi: float
    worst_case_roi: float
    
    best_case_payback_years: float # Total Investment / Annual Cash Flow
    average_case_payback_years: float
    worst_case_payback_years: float
    
    # Additional metrics
    cap_rate: float # Capitalization Rate (NOI / Purchase Price)
    cash_on_cash_return: float # (Annual Pre-tax Cash Flow / Total Cash Invested)
    debt_service_coverage_ratio: float # (NOI / Annual Debt Service)
    
    # Assumptions used in the calculation for transparency
    assumptions: Dict

class AirbnbUnderwriter:
    """
    Performs financial underwriting for potential Airbnb investment properties.
    It uses property details (scraped or provided) and financial inputs to calculate
    revenue scenarios, expenses, cash flow, ROI, and other key investment metrics.
    """
    
    def __init__(self, financial_inputs: Optional[FinancialInputs] = None):
        """
        Initializes the AirbnbUnderwriter.

        Args:
            financial_inputs: An optional FinancialInputs dataclass instance.
                              If not provided, default values from FinancialInputs will be used.
        """
        self.inputs = financial_inputs or FinancialInputs()
    
    def analyze_investment(self, subject_property: Dict, comparable_properties: List[Dict], 
                          custom_inputs_dict: Optional[Dict] = None) -> FinancialResults:
        """
        Performs a complete financial analysis of a potential Airbnb investment.

        Args:
            subject_property: A dictionary containing scraped data for the subject property.
                              Expected keys include 'price_per_night', 'num_bedrooms',
                              'num_bathrooms', 'cleaning_fee'.
            comparable_properties: A list of dictionaries, each representing a comparable property.
                                   Expected keys include 'price_per_night', 'cleaning_fee',
                                   'num_reviews', and optionally 'availability_365'.
            custom_inputs_dict: A dictionary with custom financial inputs that can override
                                the defaults or those provided during class initialization.
                                Keys should match attributes of the FinancialInputs dataclass.

        Returns:
            A FinancialResults dataclass instance containing the comprehensive analysis.
        """
        
        if custom_inputs_dict:
            self._update_inputs(custom_inputs_dict)
        
        if self.inputs.purchase_price == 0.0:
            estimated_value = self._estimate_property_value(subject_property)
            self.inputs.purchase_price = estimated_value if estimated_value is not None else 250000.0 # Default if estimation fails
            logger.info(f"Purchase price not provided, using estimated/default: ${self.inputs.purchase_price:,.2f}")
        
        loan_metrics = self._calculate_loan_metrics()
        revenue_scenarios = self._analyze_revenue_scenarios(subject_property, comparable_properties)
        monthly_op_expenses = self._calculate_monthly_operating_expenses(revenue_scenarios['average_case'])
        annual_op_expenses = monthly_op_expenses * 12
        cash_flows = self._calculate_cash_flows(revenue_scenarios, monthly_op_expenses, loan_metrics['monthly_payment'])
        roi_metrics = self._calculate_roi_metrics(cash_flows, loan_metrics['total_investment'])
        additional_metrics = self._calculate_additional_metrics(
            revenue_scenarios['average_case'], 
            annual_op_expenses,
            loan_metrics
        )
        
        current_assumptions = self._compile_assumptions()
        
        return FinancialResults(
            total_investment=loan_metrics['total_investment'],
            down_payment=loan_metrics['down_payment'],
            loan_amount=loan_metrics['loan_amount'],
            monthly_mortgage_payment=loan_metrics['monthly_payment'],
            best_case=revenue_scenarios['best_case'],
            average_case=revenue_scenarios['average_case'],
            worst_case=revenue_scenarios['worst_case'],
            monthly_operating_expenses=monthly_op_expenses,
            annual_operating_expenses=annual_op_expenses,
            best_case_monthly_cash_flow=cash_flows['best_case_monthly'],
            average_case_monthly_cash_flow=cash_flows['average_case_monthly'],
            worst_case_monthly_cash_flow=cash_flows['worst_case_monthly'],
            best_case_annual_cash_flow=cash_flows['best_case_annual'],
            average_case_annual_cash_flow=cash_flows['average_case_annual'],
            worst_case_annual_cash_flow=cash_flows['worst_case_annual'],
            best_case_roi=roi_metrics['best_case_roi'],
            average_case_roi=roi_metrics['average_case_roi'],
            worst_case_roi=roi_metrics['worst_case_roi'],
            best_case_payback_years=roi_metrics['best_case_payback'],
            average_case_payback_years=roi_metrics['average_case_payback'],
            worst_case_payback_years=roi_metrics['worst_case_payback'],
            cap_rate=additional_metrics['cap_rate'],
            cash_on_cash_return=additional_metrics['cash_on_cash_return'],
            debt_service_coverage_ratio=additional_metrics['dscr'],
            assumptions=current_assumptions
        )
    
    def _update_inputs(self, custom_inputs_dict: Dict):
        """
        Updates the financial input parameters from a dictionary.

        Args:
            custom_inputs_dict: Dictionary with keys matching FinancialInputs attributes.
        """
        for key, value in custom_inputs_dict.items():
            if hasattr(self.inputs, key):
                try:
                    # Attempt to cast to the correct type if possible (e.g. string from JSON to float)
                    field_type = type(getattr(self.inputs, key))
                    setattr(self.inputs, key, field_type(value))
                except (TypeError, ValueError) as e:
                    logger.warning(f"Could not set input '{key}' to '{value}': Type mismatch or conversion error ({e}). Using default or previous value.")
            else:
                logger.warning(f"Custom input '{key}' is not a valid financial input parameter.")
    
    def _estimate_property_value(self, subject_property: Dict) -> Optional[float]:
        """
        Estimates the property value based on limited listing data.
        This is a very rough heuristic and should be replaced by more robust valuation methods
        or actual user input for real-world applications.

        Args:
            subject_property: Dictionary with scraped property details.
                              Requires 'price_per_night', 'num_bedrooms', 'num_bathrooms'.

        Returns:
            An estimated property value as a float, or None if critical data is missing.
        """
        if not subject_property:
            logger.warning("Subject property data is empty; cannot estimate property value.")
            return None

        price_per_night = subject_property.get('price_per_night')
        num_bedrooms = subject_property.get('num_bedrooms')
        num_bathrooms = subject_property.get('num_bathrooms')

        if price_per_night is None or num_bedrooms is None or num_bathrooms is None:
            logger.warning("Cannot estimate property value: price_per_night, num_bedrooms, or num_bathrooms missing from subject_property.")
            return None

        # Heuristic: Base value on a multiple of potential gross annual room revenue.
        # This is highly speculative and varies greatly by market and property type.
        base_value = price_per_night * 365 * 15  # Example: 15x potential gross annual room revenue
        
        # Adjust based on number of bedrooms and bathrooms.
        bedroom_multiplier = 1 + (num_bedrooms * 0.2) # More bedrooms, higher value
        bathroom_multiplier = 1 + (num_bathrooms * 0.1) # More bathrooms, higher value
        
        estimated_value = base_value * bedroom_multiplier * bathroom_multiplier
        
        # Apply some sanity capping.
        estimated_value = max(50000.0, min(estimated_value, 5000000.0)) # e.g., min 50k, max 5M
        
        logger.info(f"Roughly estimated property value: ${estimated_value:,.2f}")
        return estimated_value
    
    def _calculate_loan_metrics(self) -> Dict[str, float]:
        """
        Calculates loan-related financial metrics like down payment, loan amount, and monthly mortgage.

        Returns:
            A dictionary containing 'down_payment', 'loan_amount',
            'monthly_payment', and 'total_investment'.
        """
        down_payment = self.inputs.purchase_price * (self.inputs.down_payment_percent / 100.0)
        loan_amount = self.inputs.purchase_price - down_payment
        
        monthly_interest_rate = self.inputs.loan_interest_rate / 100.0 / 12.0
        num_payments = self.inputs.loan_term_years * 12
        
        monthly_payment: float
        if num_payments == 0: # Should not happen with valid term
            monthly_payment = loan_amount
        elif monthly_interest_rate > 0:
            # Standard mortgage payment formula
            monthly_payment = loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate)**num_payments) / \
                            ((1 + monthly_interest_rate)**num_payments - 1)
        else: # Interest-free loan
            monthly_payment = loan_amount / num_payments if num_payments > 0 else loan_amount
        
        total_investment = down_payment + self.inputs.closing_costs + \
                          self.inputs.renovation_costs + self.inputs.furniture_costs
        
        return {
            'down_payment': down_payment,
            'loan_amount': loan_amount,
            'monthly_payment': monthly_payment,
            'total_investment': total_investment
        }
    
    def _analyze_revenue_scenarios(self, subject_property: Dict, comparable_properties: List[Dict]) -> Dict[str, RevenueScenario]:
        """
        Analyzes revenue scenarios (best, average, worst) based on subject property and comparables.
        Estimates ADR and occupancy for each scenario.

        Args:
            subject_property: Scraped data for the subject property.
            comparable_properties: List of scraped data for comparable properties.

        Returns:
            A dictionary ofens RevenueScenario objects, keyed by 'best_case', 'average_case', 'worst_case'.
        """
        subject_adr = subject_property.get('price_per_night', 100.0) # Default ADR if not found
        subject_cleaning_fee = subject_property.get('cleaning_fee', 0.0) # Default cleaning fee
        
        comp_adrs: List[float] = []
        comp_occupancies: List[float] = []
        comp_cleaning_fees: List[float] = []
        
        for comp in comparable_properties:
            comp_adrs.append(comp.get('price_per_night', subject_adr))
            comp_cleaning_fees.append(comp.get('cleaning_fee', subject_cleaning_fee))
            
            num_reviews = comp.get('num_reviews', 0)
            availability_365 = comp.get('availability_365', 300) # Default days available
            
            # Heuristic for occupancy: based on review frequency relative to availability.
            # Assumes more reviews suggest higher occupancy. This is a simplification.
            if num_reviews > 0 and availability_365 > 0:
                # Assume roughly 1 review per 3-5 stays. Let's use 4.
                estimated_stays_per_year = num_reviews * 4
                estimated_nights_per_year = estimated_stays_per_year * self.inputs.average_stay_length
                occupancy = min(0.95, estimated_nights_per_year / availability_365) # Cap at 95%
            else: # Default occupancy if no reviews or no availability data
                occupancy = 0.50
            comp_occupancies.append(occupancy)
        
        # Calculate market averages from comparables
        avg_market_adr = statistics.mean(comp_adrs) if comp_adrs else subject_adr
        avg_market_occupancy = statistics.mean(comp_occupancies) if comp_occupancies else 0.65 # Default market occupancy
        avg_market_cleaning_fee = statistics.mean(comp_cleaning_fees) if comp_cleaning_fees else subject_cleaning_fee
        
        # Define scenarios relative to market averages and subject property's own ADR
        # Occupancy is further adjusted by the global vacancy rate for average/worst cases.
        scenarios_params = {
            'best_case': {
                'adr_factor': 1.10, # 10% above market/subject ADR
                'occ_factor': 1.20, # 20% above market occupancy (before vacancy)
                'name': 'Best Case'
            },
            'average_case': {
                'adr_factor': 1.0,  # At market/subject ADR
                'occ_factor': 1.0,  # At market occupancy (before vacancy)
                'name': 'Average Case'
            },
            'worst_case': {
                'adr_factor': 0.85, # 15% below market/subject ADR
                'occ_factor': 0.70, # 30% below market occupancy (before vacancy)
                'name': 'Worst Case'
            }
        }
        
        scenario_results: Dict[str, RevenueScenario] = {}
        
        for scenario_key, params in scenarios_params.items():
            # Determine base ADR for scenario (higher of subject or market for upside, lower for downside)
            current_adr_base = subject_adr if scenario_key == 'worst_case' else avg_market_adr
            scenario_adr = current_adr_base * params['adr_factor']

            # Calculate scenario occupancy before applying general vacancy rate
            base_scenario_occupancy = avg_market_occupancy * params['occ_factor']
            # Effective occupancy includes the general vacancy rate adjustment
            effective_occupancy = min(0.95, base_scenario_occupancy * (1.0 - self.inputs.vacancy_rate if scenario_key != 'best_case' else 1.0))
            effective_occupancy = max(0.10, effective_occupancy) # Floor occupancy at 10%

            total_nights_booked = int(365 * effective_occupancy)
            # Ensure average_stay_length is not zero to prevent division error
            stays_per_year = (total_nights_booked / self.inputs.average_stay_length) if self.inputs.average_stay_length > 0 else 0
            
            room_revenue = total_nights_booked * scenario_adr
            cleaning_revenue_total = stays_per_year * avg_market_cleaning_fee # Use market average cleaning fee
            annual_gross_revenue = room_revenue + cleaning_revenue_total
            
            scenario_results[scenario_key] = RevenueScenario(
                scenario_name=params['name'],
                annual_revenue=annual_gross_revenue,
                monthly_revenue=annual_gross_revenue / 12.0,
                occupancy_rate=effective_occupancy,
                adr=scenario_adr,
                cleaning_revenue=cleaning_revenue_total,
                total_nights_booked=total_nights_booked
            )
        
        return scenario_results
    
    def _calculate_monthly_operating_expenses(self, average_revenue_scenario: RevenueScenario) -> float:
        """
        Calculates total fixed and variable monthly operating expenses (excluding mortgage).

        Args:
            average_revenue_scenario: The RevenueScenario object for the average case,
                                      used to calculate percentage-based expenses like management fees.
        Returns:
            Total monthly operating expenses as a float.
        """
        
        # Estimate property tax if not provided by user (e.g., 1.2% of purchase price annually)
        if self.inputs.property_tax_monthly == 0.0 and self.inputs.purchase_price > 0:
            self.inputs.property_tax_monthly = (self.inputs.purchase_price * 0.012) / 12.0
            logger.info(f"Estimated monthly property tax: ${self.inputs.property_tax_monthly:,.2f}")
        
        # Calculate property management fee based on average monthly revenue
        property_management_fee = average_revenue_scenario.monthly_revenue * (self.inputs.property_management_percent / 100.0)
        
        total_fixed_monthly_expenses = (
            self.inputs.property_tax_monthly +
            self.inputs.insurance_monthly +
            self.inputs.hoa_fees_monthly +
            self.inputs.utilities_monthly +
            self.inputs.internet_monthly +
            self.inputs.maintenance_monthly
        )
        total_monthly_op_expenses = total_fixed_monthly_expenses + property_management_fee
        
        return total_monthly_op_expenses
    
    def _calculate_cash_flows(self, revenue_scenarios: Dict[str, RevenueScenario],
                              monthly_operating_expenses: float,
                              monthly_mortgage_payment: float) -> Dict[str, float]:
        """
        Calculates monthly and annual net cash flows for all revenue scenarios.

        Args:
            revenue_scenarios: Dictionary of RevenueScenario objects.
            monthly_operating_expenses: Calculated total monthly operating expenses.
            monthly_mortgage_payment: Calculated monthly mortgage payment.

        Returns:
            A dictionary containing cash flow figures, e.g.,
            {'best_case_monthly': ..., 'best_case_annual': ...}.
        """
        cash_flows: Dict[str, float] = {}
        for scenario_key, scenario_data in revenue_scenarios.items():
            # Net cash flow = Gross Revenue - Operating Expenses - Mortgage Payment
            monthly_net_cash_flow = scenario_data.monthly_revenue - monthly_operating_expenses - monthly_mortgage_payment
            annual_net_cash_flow = monthly_net_cash_flow * 12.0
            
            cash_flows[f'{scenario_key}_monthly'] = monthly_net_cash_flow
            cash_flows[f'{scenario_key}_annual'] = annual_net_cash_flow
        return cash_flows
    
    def _calculate_roi_metrics(self, cash_flows: Dict[str, float], total_investment: float) -> Dict[str, float]:
        """
        Calculates Return on Investment (ROI) and Payback Period for all scenarios.

        Args:
            cash_flows: Dictionary containing annual cash flow for each scenario
                        (e.g., 'average_case_annual').
            total_investment: The total initial cash investment.

        Returns:
            A dictionary containing ROI and payback years for each scenario,
            e.g., {'average_case_roi': ..., 'average_case_payback': ...}.
        """
        roi_metrics: Dict[str, float] = {}
        scenarios = ['best_case', 'average_case', 'worst_case']
        
        for scenario in scenarios:
            annual_cash_flow = cash_flows.get(f'{scenario}_annual', 0.0)
            
            roi = (annual_cash_flow / total_investment) * 100.0 if total_investment > 0 else 0.0
            payback_years = total_investment / annual_cash_flow if annual_cash_flow > 0 else float('inf')
            
            roi_metrics[f'{scenario}_roi'] = roi
            roi_metrics[f'{scenario}_payback'] = payback_years
        return roi_metrics
    
    def _calculate_additional_metrics(self, average_revenue_scenario: RevenueScenario,
                                    annual_operating_expenses: float,
                                    loan_metrics: Dict[str, float]) -> Dict[str, float]:
        """
        Calculates additional investment metrics like Cap Rate, Cash-on-Cash Return, and DSCR.

        Args:
            average_revenue_scenario: RevenueScenario for the average case.
            annual_operating_expenses: Total annual operating expenses.
            loan_metrics: Dictionary containing loan details like 'monthly_payment' and 'total_investment'.

        Returns:
            A dictionary with 'cap_rate', 'cash_on_cash_return', and 'dscr'.
        """
        # Net Operating Income (NOI) = Annual Gross Revenue - Annual Operating Expenses
        net_operating_income = average_revenue_scenario.annual_revenue - annual_operating_expenses
        
        # Cap Rate = NOI / Property Purchase Price
        cap_rate = (net_operating_income / self.inputs.purchase_price) * 100.0 if self.inputs.purchase_price > 0 else 0.0
        
        # Annual Pre-Tax Cash Flow = NOI - Annual Debt Service (Mortgage Payments)
        annual_debt_service = loan_metrics['monthly_payment'] * 12.0
        annual_pre_tax_cash_flow = net_operating_income - annual_debt_service
        
        # Cash-on-Cash Return = Annual Pre-Tax Cash Flow / Total Cash Invested
        total_cash_invested = loan_metrics['total_investment']
        cash_on_cash_return = (annual_pre_tax_cash_flow / total_cash_invested) * 100.0 if total_cash_invested > 0 else 0.0

        # Debt Service Coverage Ratio (DSCR) = NOI / Annual Debt Service
        dscr = net_operating_income / annual_debt_service if annual_debt_service > 0 else float('inf') if net_operating_income > 0 else 0.0
        
        return {
            'cap_rate': cap_rate,
            'cash_on_cash_return': cash_on_cash_return,
            'dscr': dscr
        }
    
    def _compile_assumptions(self) -> Dict:
        """
        Compiles a dictionary of all financial input assumptions used in the calculations.

        Returns:
            A dictionary representing the current state of `self.inputs`.
        """
        # Using dataclasses.asdict to convert FinancialInputs instance to a dictionary
        return asdict(self.inputs)

def calculate_underwriting(subject_property: Dict, comparable_properties: List[Dict], 
                         financial_inputs_dict: Optional[Dict] = None) -> Dict:
    """
    Main public function to calculate Airbnb investment underwriting. It initializes
    the AirbnbUnderwriter class and calls its analysis method.

    Args:
        subject_property: A dictionary with scraped data for the subject property.
        comparable_properties: A list of dictionaries for comparable properties.
        financial_inputs_dict: Optional dictionary to customize financial inputs.
                               Keys should match attributes of the FinancialInputs dataclass.
    
    Returns:
        A dictionary containing the complete underwriting analysis results, structured for
        easy JSON serialization.
    """
    
    # Create FinancialInputs instance, which will hold defaults or be updated
    inputs_instance = FinancialInputs()
    
    # If custom inputs are provided, they will be applied by the AirbnbUnderwriter instance
    underwriter = AirbnbUnderwriter(inputs_instance) # Pass the instance
    
    # Perform the analysis
    results: FinancialResults = underwriter.analyze_investment(
        subject_property,
        comparable_properties,
        financial_inputs_dict # Pass the dict here for _update_inputs
    )
    
    # Convert dataclass results to dictionary for easier consumption (e.g., JSON response)
    # This manual conversion ensures the structure matches API expectations.
    return {
        'investment_summary': {
            'total_investment': results.total_investment,
            'down_payment': results.down_payment,
            'loan_amount': results.loan_amount,
            'monthly_mortgage_payment': results.monthly_mortgage_payment
        },
        'revenue_scenarios': {
            'best_case': asdict(results.best_case),
            'average_case': asdict(results.average_case),
            'worst_case': asdict(results.worst_case)
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
        'assumptions': results.assumptions # This is already a Dict from _compile_assumptions
    }
