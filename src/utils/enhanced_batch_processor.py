import pandas as pd
import streamlit as st
from datetime import datetime
import time
import json
from typing import List, Dict, Any, Optional, Tuple
import io
import numpy as np
import re

class EnhancedBatchProcessor:
    """Ultra-flexible batch processing that handles any file format"""
    
    def __init__(self, hs_agent, fallback_analyzer=None, duty_calculator=None):
        self.hs_agent = hs_agent
        self.fallback = fallback_analyzer
        self.duty_calculator = duty_calculator
        
    def detect_and_map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Intelligently detect and map columns to standard names
        Returns: (standardized_df, mapping_info)
        """
        # Normalize column names
        df = df.copy()
        original_columns = df.columns.tolist()
        df.columns = df.columns.str.strip().str.lower().str.replace(r'[^\w\s]', '', regex=True)
        
        mapping_info = {
            'original_columns': original_columns,
            'detected_mappings': {},
            'created_columns': []
        }
        
        # Define comprehensive column patterns with regex
        column_patterns = {
            'product_name': [
                r'.*product.*name.*', r'.*item.*name.*', r'.*sku.*name.*',
                r'^name$', r'^product$', r'^item$', r'^sku$', r'^title$',
                r'.*description.*1.*', r'^article$', r'^merchandise$',
                r'^goods$', r'^commodity$', r'^part.*number$'
            ],
            'description': [
                r'^description$', r'^desc$', r'.*detail.*', r'.*specification.*',
                r'.*description.*2.*', r'.*long.*desc.*', r'.*full.*desc.*',
                r'^spec$', r'^info$', r'.*information$', r'^about$',
                r'^summary$', r'^overview$', r'^features$'
            ],
            'material': [
                r'.*material.*', r'.*composition.*', r'.*fabric.*', r'.*made.*',
                r'^construction$', r'.*component.*', r'.*ingredient.*',
                r'.*substance.*', r'.*content$'
            ],
            'intended_use': [
                r'.*use.*', r'.*purpose.*', r'.*application.*', r'.*function.*',
                r'.*usage$', r'.*end.*use.*', r'.*category$', r'.*type$'
            ],
            'origin': [
                r'.*origin.*', r'.*country.*', r'.*coo$', r'.*made.*in.*',
                r'.*source.*', r'.*from$', r'.*manufactured.*', r'.*location$'
            ],
            'quantity': [
                r'.*quantity.*', r'.*qty.*', r'.*units.*', r'.*pieces.*',
                r'.*count$', r'.*amount$', r'^qty$', r'^q$'
            ],
            'unit_value': [
                r'.*unit.*price.*', r'.*unit.*value.*', r'.*price.*per.*',
                r'^price$', r'^cost$', r'.*unit.*cost.*', r'^value$'
            ],
            'customs_value': [
                r'.*customs.*value.*', r'.*total.*value.*', r'.*invoice.*',
                r'.*declared.*', r'^total$', r'.*extended.*', r'.*amount$'
            ]
        }
        
        # Try to map columns using patterns
        standardized_df = pd.DataFrame()
        columns_mapped = set()
        
        for standard_name, patterns in column_patterns.items():
            for col in df.columns:
                if col in columns_mapped:
                    continue
                    
                for pattern in patterns:
                    if re.match(pattern, col):
                        standardized_df[standard_name] = df[col]
                        mapping_info['detected_mappings'][standard_name] = original_columns[df.columns.tolist().index(col)]
                        columns_mapped.add(col)
                        break
                
                if standard_name in standardized_df.columns:
                    break
        
        # Copy over any unmapped columns (preserve extra data)
        for col in df.columns:
            if col not in columns_mapped:
                standardized_df[col] = df[col]
        
        # Intelligent fallback creation for missing critical columns
        if 'product_name' not in standardized_df.columns:
            # Try to create from any available text columns
            text_columns = df.select_dtypes(include=['object', 'string']).columns
            if len(text_columns) > 0:
                # Use the first text column as product name
                standardized_df['product_name'] = df[text_columns[0]]
                mapping_info['created_columns'].append(('product_name', f'Created from {text_columns[0]}'))
            else:
                # Create generic product names
                standardized_df['product_name'] = [f'Product_{i+1}' for i in range(len(df))]
                mapping_info['created_columns'].append(('product_name', 'Auto-generated'))
        
        if 'description' not in standardized_df.columns:
            # Try to combine available text fields
            text_columns = df.select_dtypes(include=['object', 'string']).columns
            if len(text_columns) > 1:
                # Combine multiple text columns
                standardized_df['description'] = df[text_columns].fillna('').apply(
                    lambda x: ' '.join(str(val) for val in x if val), axis=1
                )
                mapping_info['created_columns'].append(('description', 'Combined from text columns'))
            elif len(text_columns) == 1:
                standardized_df['description'] = df[text_columns[0]]
                mapping_info['created_columns'].append(('description', f'Copied from {text_columns[0]}'))
            else:
                # Use product name as description
                standardized_df['description'] = standardized_df['product_name']
                mapping_info['created_columns'].append(('description', 'Copied from product_name'))
        
        # Add empty columns for optional fields if not present
        optional_fields = ['material', 'intended_use', 'origin']
        for field in optional_fields:
            if field not in standardized_df.columns:
                standardized_df[field] = ''
        
        # Handle numeric columns for duty calculation
        numeric_fields = ['quantity', 'unit_value', 'customs_value']
        for field in numeric_fields:
            if field not in standardized_df.columns:
                standardized_df[field] = np.nan
        
        return standardized_df, mapping_info
    
    def validate_input_file(self, df: pd.DataFrame, with_duties: bool = False) -> tuple[bool, str, Dict]:
        """
        Ultra-flexible validation that accepts almost any file
        Returns: (is_valid, message, mapping_info)
        """
        # Check if dataframe is empty
        if len(df) == 0:
            return False, "The file contains no data rows", {}
        
        # Check if too many rows
        if len(df) > 100:
            return False, f"File contains {len(df)} rows. Maximum 100 products per batch. Please split your file.", {}
        
        # Detect and map columns
        standardized_df, mapping_info = self.detect_and_map_columns(df)
        
        # Update the original dataframe with standardized columns
        for col in standardized_df.columns:
            df[col] = standardized_df[col]
        
        # Create validation message
        message_parts = [f"✅ File processed successfully ({len(df)} products)"]
        
        if mapping_info['detected_mappings']:
            detected = [f"{k} ← {v}" for k, v in mapping_info['detected_mappings'].items()]
            message_parts.append(f"Detected: {', '.join(detected[:3])}")
        
        if mapping_info['created_columns']:
            created = [f"{col[0]}" for col in mapping_info['created_columns']]
            message_parts.append(f"Auto-created: {', '.join(created)}")
        
        # Check for duty calculation feasibility
        if with_duties:
            has_value_data = False
            value_columns = ['customs_value', 'unit_value', 'quantity']
            for col in value_columns:
                if col in df.columns and df[col].notna().any():
                    has_value_data = True
                    break
            
            if not has_value_data:
                message_parts.append("⚠️ No value data found - duty calculation disabled")
        
        return True, " | ".join(message_parts), mapping_info
    
    def process_batch_with_duties(self, df: pd.DataFrame, 
                                  calculate_duties: bool = False,
                                  shipping_method: str = "sea",
                                  include_mpf: bool = True,
                                  include_hmf: bool = True,
                                  progress_callback=None) -> pd.DataFrame:
        """
        Process multiple products with maximum flexibility
        """
        # Ensure columns are standardized
        standardized_df, _ = self.detect_and_map_columns(df)
        
        results = []
        total = len(standardized_df)
        
        for idx, row in standardized_df.iterrows():
            # Update progress
            if progress_callback:
                product_display = str(row.get('product_name', f'Row {idx+1}'))[:50]
                progress_callback(idx + 1, total, product_display)
            
            # Prepare product info with all available data
            product_info = {
                'product_name': str(row.get('product_name', '')).strip() or f'Product_{idx+1}',
                'description': str(row.get('description', '')).strip() or str(row.get('product_name', '')),
                'material': str(row.get('material', '')).strip(),
                'use': str(row.get('intended_use', row.get('use', ''))).strip(),
                'origin': str(row.get('origin', row.get('country_of_origin', ''))).strip()
            }
            
            # Initialize result with all original data
            row_result = row.to_dict()
            
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
                    'reasoning': (classification.get('reasoning', '')[:200] + '...') if len(classification.get('reasoning', '')) > 200 else classification.get('reasoning', ''),
                    'classification_status': 'Success'
                })
                
                # Calculate duties if requested and data available
                if calculate_duties and self.duty_calculator:
                    try:
                        duty_result = self._calculate_duties_for_row(
                            pd.Series(row_result),
                            classification.get('duty_rate', '0%'),
                            shipping_method,
                            include_mpf,
                            include_hmf
                        )
                        row_result.update(duty_result)
                    except Exception as e:
                        row_result['duty_calc_error'] = str(e)
                
            except Exception as e:
                row_result.update({
                    'hs_code': 'ERROR',
                    'confidence': '0%',
                    'duty_rate': 'N/A',
                    'reasoning': f'Classification error: {str(e)}',
                    'classification_status': 'Failed'
                })
            
            row_result['processed_at'] = datetime.now().isoformat()
            results.append(row_result)
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.5)
        
        return pd.DataFrame(results)
    
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
    
    def _calculate_duties_for_row(self, row: pd.Series, duty_rate: str, 
                                  shipping_method: str, include_mpf: bool, 
                                  include_hmf: bool) -> Dict:
        """Calculate duties for a single row with flexible value detection"""
        try:
            customs_value = 0
            
            # Try multiple ways to determine customs value
            if 'customs_value' in row and pd.notna(row['customs_value']):
                try:
                    customs_value = float(row['customs_value'])
                except:
                    pass
            
            if customs_value == 0 and 'quantity' in row and 'unit_value' in row:
                try:
                    quantity = float(row.get('quantity', 1)) if pd.notna(row.get('quantity')) else 1
                    unit_value = float(row.get('unit_value', 0)) if pd.notna(row.get('unit_value')) else 0
                    customs_value = quantity * unit_value
                except:
                    pass
            
            if customs_value == 0:
                # Try to find any column with 'total' or 'value' in it
                for col in row.index:
                    if ('total' in col.lower() or 'value' in col.lower()) and pd.notna(row[col]):
                        try:
                            customs_value = float(row[col])
                            if customs_value > 0:
                                break
                        except:
                            continue
            
            if customs_value > 0:
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
                'customs_value': 0,
                'base_duty': 0,
                'mpf': 0,
                'hmf': 0,
                'total_duties': 0,
                'total_landed_cost': 0,
                'effective_duty_rate': 'Error',
                'duty_calc_error': str(e)
            }
    
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
                'customs_value': [2550, 4375, 2400, 4250, 2325]
            }
        else:
            template_data = {
                'product_name': [
                    'LED Desk Lamp',
                    "Men's Cotton T-Shirt",
                    'Stainless Steel Water Bottle'
                ],
                'description': [
                    'Adjustable LED lamp with USB charging port',
                    'Short sleeve crew neck t-shirt',
                    'Double-wall insulated bottle'
                ],
                'material': [
                    'Aluminum, plastic',
                    '100% Cotton',
                    'Stainless steel'
                ],
                'intended_use': [
                    'Office lighting',
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
        if 'customs_value' not in df.columns:
            return {
                'total_customs_value': 0,
                'total_duties': 0,
                'total_landed_cost': 0,
                'average_duty_rate': 0,
                'message': 'No duty data available'
            }
        
        duty_df = df[(df.get('classification_status', 'Success') == 'Success') & (df['customs_value'] > 0)]
        
        if duty_df.empty:
            return {
                'total_customs_value': 0,
                'total_duties': 0,
                'total_landed_cost': 0,
                'average_duty_rate': 0,
                'message': 'No products with valid duty calculations'
            }
        
        summary = {
            'total_customs_value': duty_df['customs_value'].sum() if 'customs_value' in duty_df else 0,
            'total_base_duty': duty_df['base_duty'].sum() if 'base_duty' in duty_df else 0,
            'total_mpf': duty_df['mpf'].sum() if 'mpf' in duty_df else 0,
            'total_hmf': duty_df['hmf'].sum() if 'hmf' in duty_df else 0,
            'total_duties': duty_df['total_duties'].sum() if 'total_duties' in duty_df else 0,
            'total_landed_cost': duty_df['total_landed_cost'].sum() if 'total_landed_cost' in duty_df else 0,
            'average_effective_rate': 0,
            'products_with_duties': len(duty_df),
            'products_duty_free': 0
        }
        
        if summary['total_customs_value'] > 0:
            summary['average_effective_rate'] = (summary['total_duties'] / summary['total_customs_value'] * 100)
            summary['products_duty_free'] = len(duty_df[duty_df.get('base_duty', 0) == 0])
        
        # Group by origin if available
        if 'origin' in duty_df.columns and duty_df['origin'].notna().any():
            summary['duty_by_country'] = {
                'customs_value': duty_df.groupby('origin')['customs_value'].sum().to_dict(),
                'total_duties': duty_df.groupby('origin')['total_duties'].sum().to_dict() if 'total_duties' in duty_df else {},
                'product_name': duty_df.groupby('origin')['product_name'].count().to_dict()
            }
        
        # Group by HS code if available
        if 'hs_code' in duty_df.columns:
            summary['duty_by_hs_code'] = {
                'customs_value': duty_df.groupby('hs_code')['customs_value'].sum().to_dict(),
                'total_duties': duty_df.groupby('hs_code')['total_duties'].sum().to_dict() if 'total_duties' in duty_df else {},
                'product_name': duty_df.groupby('hs_code')['product_name'].count().to_dict()
            }
        
        # Top 5 highest duty items
        if 'total_duties' in duty_df.columns:
            summary['highest_duty_items'] = duty_df.nlargest(5, 'total_duties')[
                ['product_name', 'hs_code', 'customs_value', 'total_duties']
            ].to_dict('records')
        
        # Duty rate distribution
        if 'duty_rate' in duty_df.columns:
            summary['duty_rate_distribution'] = duty_df['duty_rate'].value_counts().to_dict()
        
        return summary