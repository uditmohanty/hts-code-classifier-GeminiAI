import os
import re
import json

try:
    import google.generativeai as genai
except Exception as e:
    genai = None


def _extract_first_json(text: str) -> dict:
    """Extract the first top-level JSON object from a string."""
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in model response.")
    return json.loads(m.group(0))


def _to_pct(value) -> str:
    """Normalize confidence to 'NN%'."""
    try:
        s = str(value).strip()
        if s.endswith("%"):
            n = float(s[:-1])
        else:
            n = float(s)
            if 0.0 <= n <= 1.0:
                n *= 100.0
        n = max(0.0, min(100.0, n))
        return f"{n:.0f}%"
    except Exception:
        return "0%"


class FallbackAnalyzer:
    """
    LLM-based fallback using Gemini. No PyTorch required.
    Returns a dict compatible with the UI.
    """

    def __init__(self, model_name: str | None = None):
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY (or GEMINI_API_KEY).")
        if genai is None:
            raise RuntimeError("Please install google-generativeai.")

        genai.configure(api_key=api_key)
        self.model_name = model_name or os.environ.get("GEMINI_TEXT_MODEL", "gemini-1.5-pro")
        self.model = genai.GenerativeModel(self.model_name)

    def analyze_unknown_product(self, product_info: dict) -> dict:
        name = product_info.get("product_name", "")
        desc = product_info.get("description", "")
        mat  = product_info.get("material", "")
        use  = product_info.get("use", "")
        org  = product_info.get("origin", "")

        prompt = f"""
You are assisting a U.S. customs broker. Classify the following product under the
U.S. Harmonized Tariff Schedule (HTSUS). Apply the General Rules of Interpretation (GRI),
consider material, function, essential character, and any specific chapter/section notes.

Return STRICT JSON ONLY with fields:
- "recommended_code": string (6–10 digit US HTS code, best available)
- "duty_rate": string (e.g., "6.5%" or "Free"; if unknown, write "N/A")
- "confidence": number 0–100 (your probability estimate this code is correct)
- "reasoning": concise explanation referencing GRI and key attributes (max 220 words)
- "alternatives": array of up to 4 plausible HTS codes (strings) if applicable
- "hts_candidates": array of up to 4 objects with:
    {{"hs_code": string, "description": string, "duty_rate": string, "relevance_score": number 0–1}}

Facts:
- Product Name: {name}
- Description: {desc}
- Material/Composition: {mat}
- Intended Use: {use}
- Country of Origin: {org}

Output JSON only. Do not include prose outside the JSON.
"""

        try:
            resp = self.model.generate_content(prompt)
            text = getattr(resp, "text", "")
            if not text and getattr(resp, "candidates", None):
                parts = resp.candidates[0].content.parts
                text = "".join(getattr(p, "text", "") for p in parts)

            data = _extract_first_json(text)

            code = str(data.get("recommended_code", "")).strip() or "N/A"
            duty = str(data.get("duty_rate", "N/A")).strip() or "N/A"
            conf = _to_pct(data.get("confidence", 0))
            reasoning = data.get("reasoning", "").strip() or "No reasoning provided."
            alts = data.get("alternatives", []) or []
            cands = data.get("hts_candidates", []) or []

            try:
                conf_num = float(conf.replace("%", ""))
            except Exception:
                conf_num = 0.0
            needs_review = conf_num < 80 or code in ("", "N/A")

            return {
                "success": True,
                "recommended_code": code,
                "duty_rate": duty,
                "confidence": conf,
                "reasoning": reasoning,
                "alternatives": alts,
                "hts_candidates": cands,
                "needs_review": needs_review,
                "source": f"LLM fallback ({self.model_name})",
            }

        except Exception as e:
            return {
                "success": False,
                "recommended_code": "N/A",
                "duty_rate": "N/A",
                "confidence": "0%",
                "reasoning": f"LLM fallback failed: {str(e)}",
                "alternatives": [],
                "hts_candidates": [],
                "needs_review": True,
                "source": f"LLM fallback ({self.model_name})",
            }
