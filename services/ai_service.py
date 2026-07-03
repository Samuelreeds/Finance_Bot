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
            # Catch the ACTUAL Google JSON error message so we know exactly why it fails
            error_details = e.response.text if e.response is not None else str(e)
            logger.warning(f"API Attempt {attempt + 1} failed. Google says: {error_details}")
            
            if attempt == 1:
                logger.error(f"API Request finally failed: {error_details}")
                raise Exception(f"Google API Error: {error_details}")
    return {}

async def analyze_and_prompt(image_bytes: bytes, details: dict) -> str:
    """Step 1: Uses Gemini REST API to analyze food image and build a prompt."""
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Switched to the universally supported public preview alias
        analysis_url = f"{BASE_URL}/gemini-3-flash-preview:generateContent?key={API_KEY}"
        
        prompt_instructions = (
            "You are an expert Art Director for a restaurant. "
            "Analyze the attached food image. DO NOT replace or change the dish. "
            f"Generate a detailed marketing poster prompt for Imagen 4.0 using these details: {json.dumps(details)}. "
            "Return ONLY the image generation prompt string."
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
        logger.error(f"analyze_and_prompt failed: {e}")
        raise e
async def generate_poster_image(prompt: str) -> bytes:
    """Step 2: Uses Imagen 4.0 REST API to render the final image."""
    try:
        imagen_url = f"{BASE_URL}/imagen-4.0-generate-001:predict?key={API_KEY}"
        
        # Note: Some Google REST endpoints use ':predict' with 'instances' for Imagen
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "3:4",
                "outputOptions": {"mimeType": "image/jpeg"}
            }
        }
        
        resp = _call_api(imagen_url, payload)
        
        # Extract base64 image from standard Imagen predict response
        b64_output = resp['predictions'][0]['bytesBase64Encoded']
        return base64.b64decode(b64_output)
    except Exception as e:
        logger.error(f"generate_poster_image failed: {e}")
        raise e

async def generate_poster(bot, file_id: str, prompt: str) -> bytes:
    """Legacy/All-in-one wrapper: Downloads Telegram image and runs full generation."""
    try:
        file = await bot.get_file(file_id)
        img_buffer = io.BytesIO()
        await file.download_to_memory(img_buffer)
        image_bytes = img_buffer.getvalue()
        
        # Run Step 1 and Step 2 sequentially
        enhanced_prompt = await analyze_and_prompt(image_bytes, {"custom_prompt": prompt})
        return await generate_poster_image(enhanced_prompt)
    except Exception as e:
        logger.error(f"generate_poster wrapper failed: {e}")
        raise e

def save_poster_history(telegram_id: str, prompt_id: int, file_id: str, image_url: str, tokens: int, status: str):
    """Preserved for database logging compatibility."""
    logger.info(f"Poster history saved - User: {telegram_id}, Status: {status}, Tokens: {tokens}")
    # Add your existing database insertion logic here if needed