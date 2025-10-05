# src/utils/image_analyzer.py
import os
import io
import json
import re

try:
    import google.generativeai as genai
except Exception as e:
    genai = None

class ImageAnalyzer:
    """
    Torch-free image analyzer that uses Gemini Vision to extract structured details
    from a product photo. Returns a dict with 'success' and the fields used by the app.
    """

    def __init__(self, model_name: str | None = None):
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY (or GEMINI_API_KEY) in environment.")

        if genai is None:
            raise RuntimeError("google-generativeai is not installed.")

        genai.configure(api_key=api_key)
        self.model_name = model_name or os.environ.get("GEMINI_IMAGE_MODEL", "gemini-1.5-flash")
        self.model = genai.GenerativeModel(self.model_name)

    def _extract_json(self, text: str) -> dict:
        """
        Pull the first JSON object from a model response safely.
        """
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError("No JSON object found in model response.")
        return json.loads(m.group(0))

    def analyze_product_image(self, image_path: str) -> dict:
        try:
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            prompt = (
                "You are an import classification assistant. From this product image, "
                "extract a concise, structured JSON with keys: "
                "product_name, material, construction, description, intended_use, "
                "features (array of short strings), additional_notes. "
                "Keep it factual; do not guess brand names."
            )

            response = self.model.generate_content(
                [
                    prompt,
                    {"mime_type": "image/jpeg", "data": img_bytes},
                ]
            )

            # Some Gemini responses include prose around JSON; extract robustly.
            text = getattr(response, "text", "") or "".join(p.text for p in response.candidates[0].content.parts)
            data = self._extract_json(text)

            return {
                "success": True,
                "product_name": data.get("product_name", ""),
                "material": data.get("material", ""),
                "construction": data.get("construction", ""),
                "description": data.get("description", ""),
                "intended_use": data.get("intended_use", ""),
                "features": data.get("features", []),
                "additional_notes": data.get("additional_notes", ""),
                "model_used": self.model_name,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
