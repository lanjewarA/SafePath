import os
import json
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Default prompt template for Gemini LLM Report Credibility Scoring
PROMPT_TEMPLATE = """You are SafePath AI's Report Verification Filter. Analyze the user-submitted safety hazard report for credibility.

Location: {location}
Report Type: {report_type}
User Description: "{description}"

Evaluate the report across these 3 criteria (0.0 to 1.0):
1. Coherence & Plausibility: Is this meaningful, realistic urban safety info?
2. Location Specificity: Does it mention specific landmarks, lighting conditions, or street features?
3. Spam/Gibberish Risk: Is this promotional text, profanity, or random keystrokes?

Return ONLY a raw JSON object with this EXACT structure (no markdown formatting, no code blocks):
{{
  "coherence_score": 0.85,
  "location_specificity": 0.80,
  "spam_probability": 0.05,
  "credibility_score": 0.86,
  "is_trustworthy": true,
  "reasoning": "Report clearly describes broken streetlights near a specific landmark with coherent details.",
  "suggested_safety_impact": -10.0
}}
"""

def heuristic_report_evaluation(location: str, report_type: str, description: str) -> Dict[str, Any]:
    """Fallback heuristic evaluator when GEMINI_API_KEY is not configured."""
    text = description.strip()
    words = text.split()

    # Rule 1: Check for short/gibberish input
    if len(text) < 10 or len(words) < 3:
        return {
            "coherence_score": 0.20,
            "location_specificity": 0.10,
            "spam_probability": 0.85,
            "credibility_score": 0.15,
            "is_trustworthy": False,
            "reasoning": "[Fallback Filter] Report text is too short or lacks meaningful detail.",
            "suggested_safety_impact": 0.0
        }

    # Rule 2: Check for obvious spam / random keystrokes
    spam_keywords = ["buy", "crypto", "casino", "free", "discount", "test", "asdf", "qwerty"]
    text_lower = text.lower()
    if any(kw in text_lower for kw in spam_keywords):
        return {
            "coherence_score": 0.30,
            "location_specificity": 0.20,
            "spam_probability": 0.90,
            "credibility_score": 0.20,
            "is_trustworthy": False,
            "reasoning": "[Fallback Filter] Report contains promotional spam or test keywords.",
            "suggested_safety_impact": 0.0
        }

    # Rule 3: Genuine safety keywords boost credibility
    safety_keywords = ["light", "dark", "broken", "cctv", "camera", "isolated", "flyover", "station", "stalk", "harass", "police", "crowd", "shadow"]
    matches = sum(1 for kw in safety_keywords if kw in text_lower)
    
    coherence = min(1.0, 0.50 + (matches * 0.15))
    specificity = min(1.0, 0.40 + (len(words) * 0.03))
    credibility = round((coherence * 0.6) + (specificity * 0.4), 2)
    is_trust = credibility >= 0.60

    impact = -15.0 if report_type in ["harassment_risk", "isolated_area"] else -8.0

    return {
        "coherence_score": round(coherence, 2),
        "location_specificity": round(specificity, 2),
        "spam_probability": 0.10,
        "credibility_score": credibility,
        "is_trustworthy": is_trust,
        "reasoning": f"[Fallback Filter] Report evaluated as {'authentic' if is_trust else 'low confidence'} based on safety keywords.",
        "suggested_safety_impact": impact if is_trust else 0.0
    }

def evaluate_report_credibility(location: str, report_type: str, description: str) -> Dict[str, Any]:
    """Evaluate report credibility using Gemini LLM API (with fallback fallback heuristic)."""
    if not GEMINI_API_KEY:
        print("[Report Trust] GEMINI_API_KEY not set. Using intelligent fallback evaluator.")
        return heuristic_report_evaluation(location, report_type, description)

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = PROMPT_TEMPLATE.format(location=location, report_type=report_type, description=description)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        raw_text = response.text.strip()
        # Clean any accidental markdown fencing
        cleaned_text = re.sub(r"^```json\s*", "", raw_text)
        cleaned_text = re.sub(r"^```\s*", "", cleaned_text)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

        result = json.loads(cleaned_text)
        return result

    except Exception as e:
        print(f"[Report Trust] Gemini API evaluation error: {e}. Falling back to heuristic filter.")
        return heuristic_report_evaluation(location, report_type, description)
