import re

def parse_form_data(text: str) -> dict:
    """Extracts key-value pairs from the user's submitted form."""
    data = {}
    lines = text.strip().split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            clean_key = key.strip().lower().replace(' ', '_')
            data[clean_key] = value.strip()
    return data

def build_prompt(prompt_template: str, form_data: dict) -> str:
    """Injects form data into the prompt template variables."""
    final_prompt = prompt_template
    
    variables = re.findall(r'\{\{(.*?)\}\}', prompt_template)
    
    for var in variables:
        clean_var = var.strip()
        value = form_data.get(clean_var, '')
        final_prompt = final_prompt.replace(f"{{{{{var}}}}}", value)
        
    return final_prompt