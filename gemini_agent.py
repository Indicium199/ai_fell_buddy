import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

class GeminiAgent:
    """Wrapper for Google Gemini API."""

    def __init__(self, model_name="gemini-2.5-flash"):
        # Load environment variables
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            raise ValueError("GEMINI_API_KEY not set in .env")
        
        self.client = genai.Client(api_key=api_key)
        self.model = model_name

    def ask_gemini(self, prompt, max_output_tokens=500):
        """Call Gemini to generate a text response."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(max_output_tokens=max_output_tokens)
            )
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            return ""
        except Exception as e:
            print("DEBUG — Gemini error:", e)
            return ""
