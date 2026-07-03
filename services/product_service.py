from services.database_service import get_connection

def get_active_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE active = 1")
    products = cursor.fetchall()
    conn.close()
    return products

def get_product_by_name(product_name):
    """Gets details for a product, ignoring uppercase/lowercase differences."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE LOWER(product_name) = LOWER(%s) AND active = 1", (product_name,))
    product = cursor.fetchone()
    conn.close()
    return product

def get_product_by_id(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def update_product_price(product_id, new_price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET unit_price = %s WHERE id = %s", (new_price, product_id))
    conn.commit()
    conn.close()