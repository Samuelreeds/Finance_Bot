import os
from dotenv import load_dotenv
from google import genai

# Load your .env file
load_dotenv()

# Initialize the client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Searching for available Imagen models...")
for model in client.models.list():
    if "imagen" in model.name:
        print(f"✅ Found: {model.name}")