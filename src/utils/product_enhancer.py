# src/utils/product_enhancer.py
import google.generativeai as genai
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config.settings import Config

class ProductEnhancer:
    """Auto-generate product details from product name"""
    
    def __init__(self):
        if not Config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        
        # Try the configured model first, fallback if it doesn't exist
        models_to_try = [
            Config.GEMINI_MODEL,  # Try gemini-2.5-flash first (from config)
            'gemini-1.5-flash',   # Fallback to 1.5-flash
            'gemini-1.5-pro',     # Try 1.5-pro
            'gemini-pro'          # Final fallback
        ]
        
        self.model = None
        self.model_name = None
        
        for model_name in models_to_try:
            try:
                self.model = genai.GenerativeModel(model_name)
                # Test the model with a simple prompt
                test_response = self.model.generate_content("Return 'OK'")
                self.model_name = model_name
                print(f"ProductEnhancer: Successfully initialized with model: {model_name}")
                break
            except Exception as e:
                print(f"ProductEnhancer: Failed to initialize {model_name}: {e}")
                continue
        
        if not self.model:
            raise ValueError(f"Could not initialize any Gemini model. Tried: {models_to_try}")
    
    def enhance_product_info(self, product_name: str) -> dict:
        """
        Generate detailed product information from product name
        
        Args:
            product_name: Simple product name from user
            
        Returns:
            dict with description, material, use, and enhanced_name
        """
        
        if not self.model:
            return {
                'enhanced_name': product_name,
                'description': '',
                'material': '',
                'intended_use': '',
                'success': False,
                'error': 'Model not initialized'
            }
        
        prompt = f"""You are a customs classification expert. Given a product name, provide detailed information needed for HTS classification.

Product Name: {product_name}

Please provide:
1. A detailed technical description (2-3 sentences) suitable for customs classification, including construction, design features, and key characteristics
2. The most likely material composition (be specific: "100% cotton", "polyester and spandex blend", "stainless steel", etc.)
3. The intended use or function (be specific about what the product is used for)
4. An enhanced product name that's more technically accurate for customs purposes

Format your response as JSON:
{{
    "enhanced_name": "More technical/formal product name",
    "description": "Detailed technical description for customs",
    "material": "Specific material composition",
    "intended_use": "Primary function or use"
}}

Important:
- Use terminology that appears in the Harmonized Tariff Schedule
- Be specific about materials (synthetic vs natural, woven vs knit, etc.)
- Include construction details (sewn, molded, assembled, etc.)
- Mention any key features relevant to classification

Return ONLY the JSON, no other text."""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            elif result_text.startswith('```'):
                result_text = result_text.replace('```', '').strip()
            
            # Try to parse the JSON
            result = json.loads(result_text)
            
            return {
                'enhanced_name': result.get('enhanced_name', product_name),
                'description': result.get('description', ''),
                'material': result.get('material', ''),
                'intended_use': result.get('intended_use', ''),
                'success': True,
                'model_used': self.model_name  # Track which model was actually used
            }
            
        except json.JSONDecodeError as e:
            # Try to extract useful info even if JSON parsing fails
            print(f"JSON parsing error: {e}")
            print(f"Response text: {result_text}")
            
            # Attempt basic parsing as fallback
            return {
                'enhanced_name': product_name,
                'description': result_text[:200] if 'result_text' in locals() else '',
                'material': '',
                'intended_use': '',
                'success': False,
                'error': f"Failed to parse AI response as JSON: {str(e)}"
            }
            
        except Exception as e:
            print(f"Error enhancing product: {e}")
            return {
                'enhanced_name': product_name,
                'description': '',
                'material': '',
                'intended_use': '',
                'success': False,
                'error': str(e)
            }

# Test function
if __name__ == "__main__":
    enhancer = ProductEnhancer()
    
    test_products = [
        "LED desk lamp",
        "Boys' swim trunks",
        "Cotton t-shirt",
        "Leather wallet",
        "Bluetooth speaker"
    ]
    
    print("Testing Product Enhancer...")
    print("=" * 60)
    print(f"Using model: {enhancer.model_name}")
    print("=" * 60)
    
    for product in test_products:
        print(f"\nProduct: {product}")
        result = enhancer.enhance_product_info(product)
        
        if result['success']:
            print(f"✓ Enhanced Name: {result['enhanced_name']}")
            print(f"  Description: {result['description'][:100]}...")
            print(f"  Material: {result['material']}")
            print(f"  Use: {result['intended_use']}")
        else:
            print(f"✗ Error: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("Test complete!")