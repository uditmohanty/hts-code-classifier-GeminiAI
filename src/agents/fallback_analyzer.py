import google.generativeai as genai
from config.settings import Config

class FallbackAnalyzer:
    """Use Gemini to analyze products not in the database"""
    
    def __init__(self):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
    
    def analyze_unknown_product(self, product_info: dict) -> dict:
        """Analyze product using LLM when no database matches found"""
        
        prompt = f"""You are a customs classification expert. A product needs classification but wasn't found in our database.

Product Information:
- Name: {product_info.get('product_name', '')}
- Description: {product_info.get('description', '')}
- Material: {product_info.get('material', '')}
- Use: {product_info.get('use', '')}
- Origin: {product_info.get('origin', '')}

Based on your knowledge of the Harmonized Tariff Schedule:

1. Identify which of the 99 chapters this product likely belongs to
2. Suggest the most likely section and heading
3. Provide reasoning based on material composition and primary function
4. Estimate a potential HS code range

Provide a detailed analysis in JSON format:
{{
  "likely_chapter": "XX",
  "chapter_name": "Chapter name",
  "suggested_heading": "XXXX",
  "reasoning": "Detailed explanation",
  "estimated_hs_range": "XXXX.XX.XXXX to XXXX.XX.XXXX",
  "confidence": "low/medium/high",
  "recommendation": "Suggest consulting customs broker for final determination"
}}"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            
            import json
            result = json.loads(result_text.strip())
            result['status'] = 'fallback_analysis'
            
            return result
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Analysis failed: {str(e)}",
                'recommendation': 'Please consult a customs broker'
            }