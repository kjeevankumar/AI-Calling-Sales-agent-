import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

try:
    print("Listing models...")
    for model in genai.list_models():
        print(f"Name: {model.name}")
        print(f"Supported methods: {model.supported_generation_methods}")
        print("-" * 30)
except Exception as e:
    print("Error listing models:", e)
