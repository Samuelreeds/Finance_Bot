from config import DELIVERY_FEE

# Define your product catalog and unit prices here
PRODUCT_CATALOG = {
    "Besdong Set": 5.00,
    "Standard Set": 10.00,
    "Premium Set": 15.00
}

def get_product_list():
    """Returns a list of available product names for the keyboard."""
    return list(PRODUCT_CATALOG.keys())

def calculate_order_total(product_name: str, quantity: int):
    """Calculates subtotal, delivery, and total based on the product."""
    unit_price = PRODUCT_CATALOG.get(product_name, 0.0)
    subtotal = unit_price * quantity
    total = subtotal + DELIVERY_FEE
    
    return subtotal, DELIVERY_FEE, total