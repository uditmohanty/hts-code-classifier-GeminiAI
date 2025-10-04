import google.generativeai as genai
import sys
import os
import json
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config.settings import Config

class ImageAnalyzer:
    """Analyze product images for customs classification"""
    
    def __init__(self):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        # Use vision-capable model
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def analyze_product_image(self, image_path: str) -> dict:
        """
        Analyze product image and extract classification details
        
        Args:
            image_path: Path to product image file
            
        Returns:
            dict with product details extracted from image
        """
        
        prompt = """Analyze this product image for customs classification purposes. 

Identify and describe:
1. Product type and name
2. Materials visible (fabric type, metal, plastic, wood, etc.)
3. Construction method (woven, knit, molded, assembled, etc.)
4. Key features (buttons, zippers, labels, patterns, etc.)
5. Intended use based on design
6. Approximate size/dimensions if discernible
7. Any visible brand names or country of origin labels

Format response as JSON:
{
    "product_name": "What the product appears to be",
    "description": "Detailed visual description",
    "material": "Materials identified from image",
    "construction": "How it's made/constructed",
    "features": ["list", "of", "key features"],
    "intended_use": "What it's used for",
    "additional_notes": "Any other relevant details"
}

Be specific and technical. Use terminology relevant to customs classification.
Return ONLY the JSON."""

        try:
            # Load and process image
            img = Image.open(image_path)
            
            # Generate analysis
            response = self.model.generate_content([prompt, img])
            result_text = response.text.strip()
            
            # Clean response
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            elif result_text.startswith('```'):
                result_text = result_text.replace('```', '').strip()
            
            result = json.loads(result_text)
            
            return {
                'product_name': result.get('product_name', ''),
                'description': result.get('description', ''),
                'material': result.get('material', ''),
                'construction': result.get('construction', ''),
                'features': result.get('features', []),
                'intended_use': result.get('intended_use', ''),
                'additional_notes': result.get('additional_notes', ''),
                'success': True
            }
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
            return {
                'product_name': '',
                'description': '',
                'material': '',
                'construction': '',
                'features': [],
                'intended_use': '',
                'additional_notes': '',
                'success': False,
                'error': str(e)
            }

if __name__ == "__main__":
    analyzer = ImageAnalyzer()
    
    # Test with an image
    test_image = "test_product.jpg"
    if os.path.exists(test_image):
        result = analyzer.analyze_product_image(test_image)
        if result['success']:
            print("Image Analysis Result:")
            print(f"Product: {result['product_name']}")
            print(f"Material: {result['material']}")
            print(f"Description: {result['description']}")
        else:
            print(f"Error: {result['error']}")
    else:
        print(f"Test image not found: {test_image}")