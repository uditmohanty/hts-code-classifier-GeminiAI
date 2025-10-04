# src/agents/gcp_gemini_classifier.py - WORKING VERSION

import google.generativeai as genai
from config.gcp_settings import GCPConfig
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GCPGeminiClassifier:
    def __init__(self):
        try:
            # Set up authentication using service account
            if GCPConfig.SERVICE_ACCOUNT_KEY:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GCPConfig.SERVICE_ACCOUNT_KEY
            
            # Configure generativeai with your project
            import google.auth
            credentials, project = google.auth.default()
            
            # Initialize the model (use gemini-pro or gemini-pro-vision)
            self.model = genai.GenerativeModel('gemini-pro')
            
            self.initialized = True
            logger.info("✓ Gemini classifier initialized with google.generativeai")
            
        except Exception as e:
            logger.error(f"✗ Failed to initialize Gemini: {str(e)}")
            # Fallback to basic classification
            self.initialized = False
            self.error = str(e)
    
    def classify_product(self, product_info, hts_candidates, cross_rulings):
        """Classify product using Gemini or fallback"""
        
        # If Gemini isn't available, use fallback classification
        if not self.initialized:
            return self._fallback_classify(product_info)
        
        try:
            # Build prompt for Gemini
            prompt = self._build_prompt(product_info, hts_candidates, cross_rulings)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Parse and return result
            return self._parse_response(response.text)
            
        except Exception as e:
            logger.error(f"Gemini classification failed: {str(e)}")
            return self._fallback_classify(product_info)
    
    def _build_prompt(self, product_info, hts_candidates, cross_rulings):
        """Build classification prompt"""
        prompt = f"""You are a US Customs classification expert. Classify this product according to the Harmonized Tariff Schedule (HTS).

Product Information:
- Name: {product_info.get('product_name')}
- Description: {product_info.get('description')}
- Material: {product_info.get('material', 'Not specified')}
- Intended Use: {product_info.get('use', 'Not specified')}
- Country of Origin: {product_info.get('origin', 'Not specified')}

Provide your classification in this exact JSON format:
{{
    "recommended_code": "XXXXXXXXXX",
    "confidence": "XX%",
    "duty_rate": "X.X%",
    "reasoning": "Clear explanation of why this HTS code was chosen"
}}

Important: Return ONLY the JSON object, no additional text."""
        
        return prompt
    
    def _parse_response(self, response_text):
        """Parse Gemini response"""
        try:
            # Extract JSON from response
            text = response_text.strip()
            
            # Find JSON in response
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = text[start:end]
                result = json.loads(json_str)
                result['status'] = 'success'
                return result
                
        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
        
        # Return with partial parsing
        return {
            'recommended_code': '9999.99.99',
            'confidence': '50%',
            'duty_rate': 'Varies',
            'reasoning': response_text[:500] if response_text else 'Unable to parse response',
            'status': 'partial'
        }
    
    def _fallback_classify(self, product_info):
        """Fallback classification when Gemini isn't available"""
        product_name = product_info.get('product_name', '').lower()
        description = product_info.get('description', '').lower()
        material = product_info.get('material', '').lower()
        
        # Basic classification rules
        classifications = {
            't-shirt': {'code': '6109.10.00', 'rate': '16.5%', 'desc': 'T-shirts, singlets, tank tops'},
            'shirt': {'code': '6205.20.00', 'rate': '19.7%', 'desc': 'Men\'s or boys\' shirts'},
            'jeans': {'code': '6203.42.40', 'rate': '16.6%', 'desc': 'Trousers of cotton'},
            'pants': {'code': '6203.42.40', 'rate': '16.6%', 'desc': 'Trousers'},
            'dress': {'code': '6204.42.00', 'rate': '16.0%', 'desc': 'Women\'s dresses'},
            'shoes': {'code': '6403.99.60', 'rate': '10.0%', 'desc': 'Footwear'},
            'laptop': {'code': '8471.30.01', 'rate': '0.0%', 'desc': 'Portable computers'},
            'phone': {'code': '8517.12.00', 'rate': '0.0%', 'desc': 'Telephones for cellular networks'},
            'watch': {'code': '9102.11.00', 'rate': '6.0%', 'desc': 'Wrist watches'},
            'bag': {'code': '4202.22.00', 'rate': '17.6%', 'desc': 'Handbags'},
        }
        
        # Check for matches
        for keyword, info in classifications.items():
            if keyword in product_name or keyword in description:
                return {
                    'recommended_code': info['code'],
                    'confidence': '40%',
                    'duty_rate': info['rate'],
                    'reasoning': f'Fallback classification: Matched keyword "{keyword}" - {info["desc"]}',
                    'status': 'fallback'
                }
        
        # Default response
        return {
            'recommended_code': '9999.99.99',
            'confidence': '10%',
            'duty_rate': 'Varies',
            'reasoning': 'Unable to classify - please consult a customs broker',
            'status': 'fallback'
        }