import os
from dotenv import load_dotenv

load_dotenv("/Users/jennygreer/ai_fell_buddy/.env")
print(os.getenv("GEMINI_API_KEY"))
