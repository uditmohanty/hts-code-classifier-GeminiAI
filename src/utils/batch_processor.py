# enhanced_batch_processor.py
# Save this file as: src/utils/enhanced_batch_processor.py

import pandas as pd
import streamlit as st
from datetime import datetime
import time
import json
from typing import List, Dict, Any, Optional
import io
import numpy as np

class EnhancedBatchProcessor:
    """Enhanced batch processing with duty calculation capabilities"""
    
    def __init__(self, hs_agent, fallback_analyzer=None, duty_calculator=None):
        self.hs_agent = hs_agent
        self.fallback = fallback_analyzer
        self.duty_calculator = duty_calculator
        
    def process_batch_with_duties(self, df: pd.DataFrame, 
                                  calculate_duties: bool = False,
                                  shipping_method: str = "sea",
                                  include_mpf: bool = True,
                                  include_hmf: bool = True,
                                  progress_callback=None) -> pd.DataFrame:
        """
        Process multiple products with optional duty calculations
        
        Expected columns: 
        - Classification: product_name, description, material, intended_use, origin
        - Duty Calculation: quantity, unit_value, customs_value (optional)
        """
        results = []
        total = len(df)
        
        for idx, row in df.iterrows():
            # Update progress
            if progress_callback:
                progress_callback(idx + 1, total, row.get('product_name', f'Row {idx+1}'))
            
            # Prepare product info for classification
            product_info = {
                'product_name': str(row.get('product_name', '')).strip(),
                'description': str(row.get('description', '')).strip(),
                'material': str(row.get('material', '')).strip(),
                'use': str(row.get('intended_use', row.get('use', ''))).strip(),
                'origin': str(row.get('origin', row.get('country_of_origin', ''))).strip()
            }
            
            # Initialize result dictionary with original data
            row_result = row.to_dict()
            
            # Skip if no product name or description
            if not product_info['product_name'] and not product_info['description']:
                row_result.update({
                    'hs_code': 'ERROR',
                    'confidence': '0%',
                    'duty_rate': 'N/A',
                    'reasoning': 'Missing product name and description',
                    'classification_status': 'Failed',
                    'base_duty': 0,
                    'total_duties': 0,
                    'total_landed_cost': row.get('customs_value', 0)
                })
            else:
                try:
                    # Classify product
                    classification = self.hs_agent.classify_product(product_info)
                    
                    # Check if fallback needed
                    confidence = self._parse_confidence(classification.get('confidence', 0))
                    if self.fallback and confidence < 50:
                        classification = self.fallback.analyze_unknown_product(product_info)
                    
                    # Update result with classification
                    row_result.update({
                        'hs_code': classification.get('recommended_code', 'N/A'),
                        'confidence': classification.get('confidence', '0%'),
                        'duty_rate': classification.get('duty_rate', 'N/A'),
                        'reasoning': classification.get('reasoning', '')[:200],
                        'classification_status': 'Success'
                    })
                    
                    # Calculate duties if requested and calculator available
                    if calculate_duties and self.duty_calculator:
                        duty_result = self._calculate_duties_for_row(
                            row, 
                            classification.get('duty_rate', '0%'),
                            shipping_method,
                            include_mpf,
                            include_hmf
                        )
                        row_result.update(duty_result)
                    
                except Exception as e:
                    row_result.update({
                        'hs_code': 'ERROR',
                        'confidence': '0%',
                        'duty_rate': 'N/A',
                        'reasoning': f'Error: {str(e)}',
                        'classification_status': 'Failed',
                        'base_duty': 0,
                        'total_duties': 0
                    })
            
            row_result['processed_at'] = datetime.now().isoformat()
            results.append(row_result)
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.5)
        
        return pd.DataFrame(results)
    
    def _calculate_duties_for_row(self, row: pd.Series, duty_rate: str, 
                                  shipping_method: str, include_mpf: bool, 
                                  include_hmf: bool) -> Dict:
        """Calculate duties for a single row"""
        try:
            # Determine customs value
            customs_value = 0
            
            # Option 1: Direct customs_value column
            if 'customs_value' in row and pd.notna(row['customs_value']):
                customs_value = float(row['customs_value'])
            
            # Option 2: Calculate from quantity and unit_value
            elif 'quantity' in row and 'unit_value' in row:
                quantity = float(row.get('quantity', 1)) if pd.notna(row.get('quantity')) else 1
                unit_value = float(row.get('unit_value', 0)) if pd.notna(row.get('unit_value')) else 0
                customs_value = quantity * unit_value
            
            # Option 3: Use FOB + freight + insurance
            elif 'fob_value' in row:
                fob = float(row.get('fob_value', 0)) if pd.notna(row.get('fob_value')) else 0
                freight = float(row.get('freight', 0)) if pd.notna(row.get('freight')) else 0
                insurance = float(row.get('insurance', 0)) if pd.notna(row.get('insurance')) else 0
                customs_value = fob + freight + insurance
            
            if customs_value > 0:
                # Calculate duties
                duty_calc = self.duty_calculator.calculate_duties(
                    customs_value=customs_value,
                    duty_rate=duty_rate,
                    shipping_method=shipping_method,
                    include_mpf=include_mpf,
                    include_hmf=include_hmf
                )
                
                return {
                    'customs_value': customs_value,
                    'base_duty': duty_calc['base_duty'],
                    'mpf': duty_calc['mpf'],
                    'hmf': duty_calc['hmf'],
                    'total_duties': duty_calc['total_duties_and_fees'],
                    'total_landed_cost': duty_calc['total_landed_cost'],
                    'effective_duty_rate': f"{duty_calc['effective_duty_rate']:.2f}%"
                }
            else:
                return {
                    'customs_value': 0,
                    'base_duty': 0,
                    'mpf': 0,
                    'hmf': 0,
                    'total_duties': 0,
                    'total_landed_cost': 0,
                    'effective_duty_rate': '0.00%'
                }
                
        except Exception as e:
            return {
                'customs_value': row.get('customs_value', 0),
                'base_duty': 0,
                'mpf': 0,
                'hmf': 0,
                'total_duties': 0,
                'total_landed_cost': row.get('customs_value', 0),
                'effective_duty_rate': 'Error',
                'duty_calc_error': str(e)
            }
    
    def _parse_confidence(self, conf_value) -> float:
        """Parse confidence value to float"""
        try:
            s = str(conf_value).strip().replace('%', '')
            n = float(s)
            if 0.0 <= n <= 1.0:
                n *= 100.0
            return max(0.0, min(100.0, n))
        except:
            return 0.0
    
    def validate_input_file(self, df: pd.DataFrame, with_duties: bool = False) -> tuple[bool, str]:
        """
        Validate the input dataframe has required columns
        Returns (is_valid, message)
        """
        # Classification columns
        required_columns = ['product_name', 'description']
        optional_columns = ['material', 'intended_use', 'origin', 'country_of_origin', 'use']
        
        # Duty calculation columns (all optional)
        duty_columns = ['quantity', 'unit_value', 'customs_value', 'fob_value', 'freight', 'insurance']
        
        # Check for required columns
        missing_required = []
        for col in required_columns:
            if col not in df.columns:
                missing_required.append(col)
        
        if missing_required:
            return False, f"Missing required columns: {', '.join(missing_required)}"
        
        # Add optional columns if they don't exist
        for col in optional_columns + duty_columns:
            if col not in df.columns:
                df[col] = np.nan if col in duty_columns else ''
        
        # Check if dataframe is empty
        if len(df) == 0:
            return False, "The file contains no data rows"
        
        # Check if too many rows
        if len(df) > 100:
            return False, "File contains too many rows. Maximum 100 products per batch."
        
        # If duty calculation requested, check for value columns
        if with_duties:
            has_value_data = False
            for idx, row in df.iterrows():
                if (pd.notna(row.get('customs_value')) and row.get('customs_value') > 0) or \
                   (pd.notna(row.get('unit_value')) and row.get('unit_value') > 0) or \
                   (pd.notna(row.get('fob_value')) and row.get('fob_value') > 0):
                    has_value_data = True
                    break
            
            if not has_value_data:
                return False, "Duty calculation requested but no value data found. Add customs_value, unit_value, or fob_value columns."
        
        return True, f"File validated successfully ({len(df)} products)"
    
    def create_template(self, include_duty_fields: bool = True) -> bytes:
        """Create a CSV template for batch upload"""
        if include_duty_fields:
            template_data = {
                'product_name': [
                    'LED Desk Lamp',
                    "Men's Cotton T-Shirt",
                    'Stainless Steel Water Bottle',
                    'Wireless Bluetooth Headphones',
                    'Yoga Mat'
                ],
                'description': [
                    'Adjustable LED lamp with USB charging port, metal base',
                    'Short sleeve crew neck t-shirt, 100% cotton, size L',
                    'Double-wall insulated bottle, 750ml capacity',
                    'Over-ear headphones with noise cancellation',
                    'Non-slip exercise mat, 6mm thickness'
                ],
                'material': [
                    'Aluminum, plastic, LED',
                    '100% Cotton',
                    'Stainless steel 304',
                    'Plastic, foam padding',
                    'TPE (Thermoplastic Elastomer)'
                ],
                'intended_use': [
                    'Office/home lighting',
                    'Casual wear',
                    'Beverage container',
                    'Audio listening',
                    'Exercise and yoga'
                ],
                'origin': [
                    'China',
                    'Bangladesh',
                    'India',
                    'Vietnam',
                    'Taiwan'
                ],
                'quantity': [100, 500, 200, 50, 150],
                'unit_value': [25.50, 8.75, 12.00, 85.00, 15.50],
                'customs_value': [2550, 4375, 2400, 4250, 2325]  # quantity * unit_value
            }
        else:
            template_data = {
                'product_name': [
                    'LED Desk Lamp',
                    "Men's Cotton T-Shirt",
                    'Stainless Steel Water Bottle'
                ],
                'description': [
                    'Adjustable LED lamp with USB charging port, metal base',
                    'Short sleeve crew neck t-shirt, 100% cotton, size L',
                    'Double-wall insulated bottle, 750ml capacity'
                ],
                'material': [
                    'Aluminum, plastic, LED',
                    '100% Cotton',
                    'Stainless steel 304'
                ],
                'intended_use': [
                    'Office/home lighting',
                    'Casual wear',
                    'Beverage container'
                ],
                'origin': [
                    'China',
                    'Bangladesh',
                    'India'
                ]
            }
        
        df = pd.DataFrame(template_data)
        return df.to_csv(index=False).encode('utf-8')
    
    def generate_duty_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for duty calculations"""
        
        # Filter only successful classifications with duty data
        duty_df = df[(df['classification_status'] == 'Success') & (df['customs_value'] > 0)]
        
        if duty_df.empty:
            return {
                'total_customs_value': 0,
                'total_duties': 0,
                'total_landed_cost': 0,
                'average_duty_rate': 0,
                'duty_by_country': {},
                'duty_by_hs_code': {}
            }
        
        summary = {
            'total_customs_value': duty_df['customs_value'].sum(),
            'total_base_duty': duty_df['base_duty'].sum(),
            'total_mpf': duty_df['mpf'].sum(),
            'total_hmf': duty_df['hmf'].sum(),
            'total_duties': duty_df['total_duties'].sum(),
            'total_landed_cost': duty_df['total_landed_cost'].sum(),
            'average_effective_rate': (duty_df['total_duties'].sum() / duty_df['customs_value'].sum() * 100) if duty_df['customs_value'].sum() > 0 else 0,
            'products_with_duties': len(duty_df),
            'products_duty_free': len(duty_df[duty_df['base_duty'] == 0]),
            
            # Group by country
            'duty_by_country': duty_df.groupby('origin').agg({
                'customs_value': 'sum',
                'total_duties': 'sum',
                'product_name': 'count'
            }).to_dict(),
            
            # Group by HS code
            'duty_by_hs_code': duty_df.groupby('hs_code').agg({
                'customs_value': 'sum',
                'total_duties': 'sum',
                'product_name': 'count'
            }).to_dict(),
            
            # Top 5 highest duty items
            'highest_duty_items': duty_df.nlargest(5, 'total_duties')[
                ['product_name', 'hs_code', 'customs_value', 'total_duties']
            ].to_dict('records'),
            
            # Duty rate distribution
            'duty_rate_distribution': duty_df['duty_rate'].value_counts().to_dict()
        }
        
        return summary