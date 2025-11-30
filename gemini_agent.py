#file: gemini_agent.py

import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

class GeminiAgent:
    """Wrapper for Google Gemini API (new SDK) using model gemini-2.5-flash-lite."""

    def __init__(self, model_name="gemini-2.5-flash-lite"):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing from .env")

        # Create client
        self.client = genai.Client(api_key=api_key)
        self.model = model_name

    def ask_gemini(self, prompt, max_output_tokens=500):
        """Send a prompt to Gemini using the 2.x generation API."""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens
                )
            )

            # Normal response path
            if hasattr(response, "text") and response.text:
                return response.text.strip()

            return ""

        except Exception as e:
            print("DEBUG — Gemini error:", e)
            return ""


# Optional: quick test
if __name__ == "__main__":
    agent = GeminiAgent()
    print("Sending test prompt...")
    reply = agent.ask_gemini("Hi! Can you hear me?")
    print("Response:", reply or "[No text returned]")
