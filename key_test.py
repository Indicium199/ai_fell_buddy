from dotenv import load_dotenv
import os
load_dotenv("/path/to/.env", override=True)

from google import genai  # or whichever SDK
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
