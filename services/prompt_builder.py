# services/prompt_builder.py

TEMPLATES = {
    "minimal": {
        "style_prompt": "Minimalist luxury, white background, high-end negative space usage, modern sans-serif typography, editorial food photography style.",
        "description": "Premium, White background, Large food, Modern typography"
    },
    "promotion": {
        "style_prompt": "High-energy commercial marketing, bold typography, large vibrant 'SALE' badge, strong contrast, social media layout, dynamic background.",
        "description": "Bold, Discount focused, Large SALE badge"
    },
    "luxury": {
        "style_prompt": "Dark moody cinema-style, gold accents, elegant serif typography, high-end fine dining ambiance, dramatic lighting, luxury branding.",
        "description": "Dark background, Elegant typography, Gold accents"
    }
}

def build_poster_prompt(details: dict, template_id: str, food_description: str) -> str:
    """Assembles the final prompt based on template and user data."""
    template = TEMPLATES.get(template_id, TEMPLATES["minimal"])
    
    prompt = f"""
    Create a professional restaurant poster.
    Subject: {food_description} (DO NOT replace or change the dish. Use it exactly as provided).
    
    Layout/Style Guide ({template['description']}):
    {template['style_prompt']}
    
    Branding & Text:
    - Headline: {details.get('food_name', 'Our Special')}
    - Promotion: {details.get('promotion', '')}
    - Price: {details.get('price', '')}
    - Original Price: {details.get('original_price', '')}
    - Theme Color Scheme: {details.get('theme_color', 'Neutral')}
    
    Footer Info (ONLY if provided):
    {details.get('phone', '')} {details.get('address', '')} {details.get('website', '')}
    
    Ensure: High-end quality, photorealistic, Instagram-ready composition.
    """
    return prompt