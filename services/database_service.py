import pymysql
from urllib.parse import urlparse
from config import DATABASE_URL
from utils.logger import logger

def get_connection():
    clean_url = DATABASE_URL.replace("mysql+pymysql://", "mysql://")
    url = urlparse(clean_url)
    
    return pymysql.connect(
        host=url.hostname,
        user=url.username,
        password=url.password or "",
        database=url.path[1:],
        port=url.port or 3306,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    logger.info("Verifying MySQL database and schemas...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # [Keep existing products, orders, expenses, income tables here]
        
        # New AI Poster Tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poster_prompts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                prompt TEXT NOT NULL,
                active BOOLEAN DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poster_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                telegram_id VARCHAR(255) NOT NULL,
                prompt_id INT NOT NULL,
                telegram_image_file_id VARCHAR(255) NOT NULL,
                generated_image_url TEXT,
                tokens_used INT NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tokens (
                telegram_id VARCHAR(255) PRIMARY KEY,
                balance INT DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value VARCHAR(255) NOT NULL
            )
        ''')
        
        # Insert defaults if missing
        cursor.execute("INSERT IGNORE INTO settings (setting_key, setting_value) VALUES ('poster_price', '10')")
        cursor.execute("INSERT IGNORE INTO poster_prompts (name, prompt) VALUES ('Classic Restaurant', 'A premium restaurant advertising poster with cinematic lighting, elegant typography, luxury food photography...')")
        
        conn.commit()
        conn.close()
        logger.info("Database schemas verified.")
    except Exception as e:
        logger.error(f"Database error: {e}")

# [Keep existing save_order, save_expense, save_income methods here]

def save_order(customer_name, phone, address, product_id, quantity, unit_price, delivery_fee, total_price, delivery_date, created_by):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(id) as count FROM orders")
    result = cursor.fetchone()
    count = (result['count'] + 1) if result and result['count'] else 1
    order_number = f"#{count:04d}"
    
    cursor.execute('''
        INSERT INTO orders (order_number, customer_name, phone, address, product_id, quantity, unit_price, delivery_fee, total_price, delivery_date, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (order_number, customer_name, phone, address, product_id, quantity, unit_price, delivery_fee, total_price, delivery_date, created_by))
    
    conn.commit()
    conn.close()
    return order_number

def save_expense(amount, description, telegram_file_id, created_by):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO expenses (amount, description, telegram_file_id, created_by)
        VALUES (%s, %s, %s, %s)
    ''', (amount, description, telegram_file_id, created_by))
    
    conn.commit()
    conn.close()

def save_income(amount, description, telegram_file_id, created_by):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO income (amount, description, telegram_file_id, created_by)
        VALUES (%s, %s, %s, %s)
    ''', (amount, description, telegram_file_id, created_by))
    
    conn.commit()
    conn.close()

# ... (Keep get_today_order_income and get_report_data exactly as they were)
def get_today_order_income():
    """Gets total count and revenue from today's orders (used for the /income command)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(id) as count, COALESCE(SUM(total_price), 0) as total 
        FROM orders 
        WHERE DATE(created_at) = CURDATE()
    ''')
    result = cursor.fetchone()
    conn.close()
    
    return result['count'], float(result['total'])

def get_report_data(start_date, end_date):
    """Calculates total orders, income, and expenses for a specific date range."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Calculate Income (from automated Orders)
    cursor.execute('''
        SELECT COUNT(id) as count, COALESCE(SUM(total_price), 0) as total 
        FROM orders 
        WHERE DATE(created_at) >= %s AND DATE(created_at) <= %s
    ''', (start_date, end_date))
    order_data = cursor.fetchone()
    order_count = order_data['count']
    income_total = float(order_data['total'])
    
    # 2. Calculate Expenses
    cursor.execute('''
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM expenses 
        WHERE DATE(created_at) >= %s AND DATE(created_at) <= %s
    ''', (start_date, end_date))
    expense_total = float(cursor.fetchone()['total'])
    
    conn.close()
    return order_count, income_total, expense_total