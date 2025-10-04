import google.generativeai as genai
from config.settings import Config
import json

genai.configure(api_key=Config.GOOGLE_API_KEY)

class GeminiClassifier:
    def __init__(self):
        
        self.model = genai.GenerativeModel('gemini-2.5-flash')  # Use this instead
    
    def build_classification_prompt(self, product_info: dict, hts_candidates: list, cross_rulings: list) -> str:
        prompt = f"""You are a U.S. customs classification expert. Classify this product using HTSUS rules.

Product Information:
- Name: {product_info.get('product_name', '')}
- Description: {product_info.get('description', '')}
- Material: {product_info.get('material', '')}
- Use: {product_info.get('use', '')}
- Origin: {product_info.get('origin', '')}

Candidate HTS Codes:
{json.dumps(hts_candidates[:3], indent=2)}

Apply GRI rules and choose the most specific 10-digit HTS code.

Return ONLY valid JSON:
{{
  "recommended_code": "####.##.####",
  "duty_rate": "X%",
  "confidence": "NN%",
  "reasoning": "Brief explanation applying GRI rules",
  "alternatives": ["####.##.####", "####.##.####"]
}}"""
        return prompt
    
    def classify_product(self, product_info: dict, hts_candidates: list, cross_rulings: list) -> dict:
        prompt = self.build_classification_prompt(product_info, hts_candidates, cross_rulings)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            return result
            
        except Exception as e:
            print(f"Gemini error: {e}")
            return {
                "recommended_code": "Error",
                "duty_rate": "N/A",
                "confidence": "0%",
                "reasoning": f"Classification failed: {str(e)}",
                "alternatives": []
            }