import vertexai
from vertexai.generative_models import GenerativeModel
from config.gcp_settings import GCPConfig
import json

class GCPGeminiClassifier:
    def __init__(self):
        # Initialize Vertex AI
        vertexai.init(
            project=GCPConfig.PROJECT_ID, 
            location=GCPConfig.REGION
        )
        self.model = GenerativeModel(GCPConfig.GEMINI_MODEL)
    
    def classify_product(self, product_info: dict, hts_candidates: list, cross_rulings: list) -> dict:
        """Use Vertex AI Gemini for classification"""
        
        prompt = self._build_prompt(product_info, hts_candidates, cross_rulings)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'top_p': 0.95,
                    'max_output_tokens': 2048,
                }
            )
            
            result_text = response.text
            
            # Parse JSON response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            return result
            
        except Exception as e:
            print(f"Classification error: {e}")
            return {
                "recommended_code": "Error",
                "duty_rate": "N/A",
                "confidence": "0%",
                "reasoning": f"Classification failed: {str(e)}",
                "alternatives": []
            }
    
    def _build_prompt(self, product_info, hts_candidates, cross_rulings):
        """Build classification prompt"""
        
        return f"""You are a U.S. customs classification expert. Your task is to assign the correct HTSUS code to imported goods.

**Product Information:**
- Name: {product_info.get('product_name', '')}
- Description: {product_info.get('description', '')}
- Material/Composition: {product_info.get('material', '')}
- Intended Use: {product_info.get('use', '')}
- Country of Origin: {product_info.get('origin', '')}

**Candidate HTS Codes from Database:**
{json.dumps(hts_candidates[:3], indent=2)}

**Relevant CROSS Rulings:**
{json.dumps(cross_rulings[:2], indent=2)}

**Instructions:**
1. Apply the General Rules of Interpretation (GRI 1-6)
2. Choose the most specific subheading that matches the description
3. If multiple codes may apply, select the best match and provide alternatives
4. Provide clear reasoning in plain English

**Output Format (JSON only):**
{{
  "recommended_code": "####.##.####",
  "duty_rate": "X%",
  "confidence": "NN%",
  "reasoning": "Brief explanation applying GRI rules",
  "alternatives": ["####.##.####"]
}}

Return ONLY valid JSON."""