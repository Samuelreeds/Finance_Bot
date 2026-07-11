import os
import io
import json
import base64
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

def _call_api(url: str, payload: dict) -> dict:
    """Helper to perform REST API calls with a single retry on failure."""
    headers = {'Content-Type': 'application/json'}
    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_details = e.response.text if e.response is not None else str(e)
            logger.warning(f"API Attempt {attempt + 1} failed. Google says: {error_details}")
            
            if attempt == 1:
                logger.error(f"API Request finally failed: {error_details}")
                raise Exception(f"Google API Error: {error_details}")
    return {}

async def analyze_food_image(image_bytes: bytes) -> str:
    """Step 1: Uses Gemini REST API to analyze the uploaded food photo to preserve the core subject."""
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        analysis_url = f"{BASE_URL}/gemini-3-flash-preview:generateContent?key={API_KEY}"
        
        prompt_instructions = (
            "You are an expert food photographer. Analyze the attached food image. "
            "Describe the food item in extreme detail (ingredients, colors, textures, and plating style). "
            "DO NOT describe the background, lighting, or style. ONLY describe the food itself. "
            "Return ONLY the description string."
        )
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_instructions},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}
                ]
            }]
        }
        
        resp = _call_api(analysis_url, payload)
        return resp['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"analyze_food_image failed: {e}")
        raise e

async def generate_poster_image(prompt: str) -> bytes:
    """Step 2: Uses Imagen 4.0 REST API to render the final template-injected image."""
    try:
        imagen_url = f"{BASE_URL}/imagen-4.0-generate-001:predict?key={API_KEY}"
        
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "3:4",
                "outputOptions": {"mimeType": "image/jpeg"}
            }
        }
        
        resp = _call_api(imagen_url, payload)
        b64_output = resp['predictions'][0]['bytesBase64Encoded']
        return base64.b64decode(b64_output)
    except Exception as e:
        logger.error(f"generate_poster_image failed: {e}")
        raise e

def save_poster_history(telegram_id: str, prompt_id: int, file_id: str, image_url: str, tokens: int, status: str):
    """Preserved for database logging compatibility."""
    logger.info(f"Poster history saved - User: {telegram_id}, Status: {status}, Tokens: {tokens}")