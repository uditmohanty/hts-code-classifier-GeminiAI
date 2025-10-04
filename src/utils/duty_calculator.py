from datetime import datetime
from typing import Dict, Optional

class DutyCalculator:
    """Calculate import duties and fees for products"""
    
    # US Customs fees (as of 2025)
    MPF_RATE = 0.003464  # Merchandise Processing Fee: 0.3464%
    MPF_MIN = 27.75      # Minimum MPF
    MPF_MAX = 538.40     # Maximum MPF
    
    HMF_RATE = 0.00125   # Harbor Maintenance Fee: 0.125% (for sea shipments)
    
    def __init__(self):
        self.calculation_history = []
    
    def parse_duty_rate(self, duty_rate_str: str) -> float:
        """
        Parse duty rate string to float
        Examples: "5.5%", "Free", "$0.42/kg", "3.4% + $0.25/kg"
        """
        if not duty_rate_str or duty_rate_str.lower() in ['free', 'n/a', 'none']:
            return 0.0
        
        # Extract percentage if present
        if '%' in duty_rate_str:
            try:
                # Get first number before %
                rate = float(duty_rate_str.split('%')[0].split('+')[0].strip())
                return rate / 100  # Convert to decimal
            except:
                return 0.0
        
        return 0.0
    
    def calculate_duties(self, 
                        customs_value: float,
                        duty_rate: str,
                        shipping_method: str = "sea",
                        include_mpf: bool = True,
                        include_hmf: bool = True,
                        preferential_rate: Optional[str] = None) -> Dict:
        """
        Calculate total import duties and fees
        
        Args:
            customs_value: Declared value of goods (CIF value)
            duty_rate: Duty rate string from HTS (e.g., "5.5%")
            shipping_method: "sea" or "air"
            include_mpf: Include Merchandise Processing Fee
            include_hmf: Include Harbor Maintenance Fee (sea only)
            preferential_rate: Special trade program rate if applicable
        
        Returns:
            Dictionary with breakdown of all charges
        """
        
        # Use preferential rate if provided
        effective_duty_rate_str = preferential_rate if preferential_rate else duty_rate
        duty_rate_decimal = self.parse_duty_rate(effective_duty_rate_str)
        
        # Base duty calculation
        base_duty = customs_value * duty_rate_decimal
        
        # MPF calculation (0.3464% of value, min $27.75, max $538.40)
        mpf = 0
        if include_mpf:
            mpf = customs_value * self.MPF_RATE
            mpf = max(self.MPF_MIN, min(mpf, self.MPF_MAX))
        
        # HMF calculation (0.125% for sea shipments)
        hmf = 0
        if include_hmf and shipping_method.lower() == "sea":
            hmf = customs_value * self.HMF_RATE
        
        # Total calculation
        total_duties = base_duty + mpf + hmf
        total_landed_cost = customs_value + total_duties
        
        # Effective duty rate
        effective_rate = (total_duties / customs_value * 100) if customs_value > 0 else 0
        
        result = {
            'customs_value': customs_value,
            'duty_rate_applied': effective_duty_rate_str,
            'duty_rate_decimal': duty_rate_decimal,
            'base_duty': base_duty,
            'mpf': mpf,
            'hmf': hmf,
            'total_duties_and_fees': total_duties,
            'total_landed_cost': total_landed_cost,
            'effective_duty_rate': effective_rate,
            'calculation_date': datetime.now().isoformat()
        }
        
        self.calculation_history.append(result)
        return result
    
    def calculate_from_invoice(self,
                               fob_value: float,
                               freight_cost: float,
                               insurance_cost: float,
                               duty_rate: str,
                               shipping_method: str = "sea") -> Dict:
        """
        Calculate duties from invoice components
        
        Args:
            fob_value: Free on Board value (product cost)
            freight_cost: International shipping cost
            insurance_cost: Insurance cost
            duty_rate: Duty rate from HTS
            shipping_method: "sea" or "air"
        
        Returns:
            Complete calculation breakdown
        """
        # CIF value = Cost + Insurance + Freight
        cif_value = fob_value + freight_cost + insurance_cost
        
        result = self.calculate_duties(
            customs_value=cif_value,
            duty_rate=duty_rate,
            shipping_method=shipping_method
        )
        
        # Add invoice breakdown
        result['invoice_breakdown'] = {
            'fob_value': fob_value,
            'freight_cost': freight_cost,
            'insurance_cost': insurance_cost,
            'cif_value': cif_value
        }
        
        return result
    
    def compare_rates(self,
                     customs_value: float,
                     standard_rate: str,
                     preferential_rate: str,
                     program_name: str = "Free Trade Agreement") -> Dict:
        """
        Compare standard vs preferential duty rates
        
        Args:
            customs_value: Declared value
            standard_rate: Normal HTS rate
            preferential_rate: FTA or GSP rate
            program_name: Name of preferential program
        
        Returns:
            Comparison of both scenarios
        """
        standard = self.calculate_duties(customs_value, standard_rate)
        preferential = self.calculate_duties(customs_value, preferential_rate)
        
        savings = standard['total_duties_and_fees'] - preferential['total_duties_and_fees']
        savings_percent = (savings / standard['total_duties_and_fees'] * 100) if standard['total_duties_and_fees'] > 0 else 0
        
        return {
            'standard': standard,
            'preferential': preferential,
            'program_name': program_name,
            'savings': savings,
            'savings_percent': savings_percent
        }
    
    def format_currency(self, amount: float) -> str:
        """Format amount as USD currency"""
        return f"${amount:,.2f}"
    
    def get_calculation_summary(self, result: Dict) -> str:
        """Generate text summary of calculation"""
        summary = f"""
        DUTY CALCULATION SUMMARY
        ========================
        Customs Value (CIF): {self.format_currency(result['customs_value'])}
        Duty Rate Applied: {result['duty_rate_applied']}
        
        BREAKDOWN:
        - Base Duty: {self.format_currency(result['base_duty'])}
        - MPF (Merchandise Processing Fee): {self.format_currency(result['mpf'])}
        - HMF (Harbor Maintenance Fee): {self.format_currency(result['hmf'])}
        
        Total Duties & Fees: {self.format_currency(result['total_duties_and_fees'])}
        Total Landed Cost: {self.format_currency(result['total_landed_cost'])}
        Effective Duty Rate: {result['effective_duty_rate']:.2f}%
        """
        return summary