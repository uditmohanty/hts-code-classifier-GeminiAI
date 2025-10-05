import os
import json
import re

try:
    import google.generativeai as genai
except Exception:
    genai = None


class ImageAnalyzer:
    """Torch-free analyzer using Gemini Vision to extract product details."""

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
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise ValueError("No JSON object found in model response.")
        return json.loads(m.group(0))

    def analyze_product_image(self, image_path: str) -> dict:
        try:
            with open(image_path, "rb") as f:
                img_bytes = f.read()

            prompt = (
                "From this product image, return STRICT JSON with keys: "
                "product_name, material, construction, description, intended_use, "
                "features (array), additional_notes."
            )

            resp = self.model.generate_content(
                [prompt, {"mime_type": "image/jpeg", "data": img_bytes}]
            )
            text = getattr(resp, "text", "")
            if not text and getattr(resp, "candidates", None):
                parts = resp.candidates[0].content.parts
                text = "".join(getattr(p, "text", "") for p in parts)

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
