def parse_template(text):
    """
    Reads any text, ignores blank lines and decorative equals signs, 
    and extracts Key: Value pairs into a dictionary.
    """
    data = {}
    if not text:
        return data
        
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('==='):
            continue
            
        if ':' in line:
            key, val = line.split(':', 1)
            # Remove spaces and make lowercase for robust tracking
            data[key.strip().lower()] = val.strip()
            
    return data

def validate_order(data):
    """Checks if all required order fields are present."""
    required = ['customer', 'phone number', 'address', 'product', 'quantity', 'delivery date']
    missing = [f.title() for f in required if not data.get(f)]
    return missing

def validate_finance(data):
    """Checks if all required expense/income fields are present."""
    required = ['amount', 'description']
    missing = [f.title() for f in required if not data.get(f)]
    return missing