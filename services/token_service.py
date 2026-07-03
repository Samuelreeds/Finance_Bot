from services.database_service import get_connection

def get_balance(telegram_id: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_tokens WHERE telegram_id = %s", (telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result['balance'] if result else 0

def add_tokens(telegram_id: str, amount: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_tokens (telegram_id, balance) 
        VALUES (%s, %s) 
        ON DUPLICATE KEY UPDATE balance = balance + %s
    ''', (telegram_id, amount, amount))
    conn.commit()
    conn.close()

def deduct_tokens(telegram_id: str, amount: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM user_tokens WHERE telegram_id = %s FOR UPDATE", (telegram_id,))
    result = cursor.fetchone()
    
    if not result or result['balance'] < amount:
        conn.rollback()
        conn.close()
        return False
        
    cursor.execute("UPDATE user_tokens SET balance = balance - %s WHERE telegram_id = %s", (amount, telegram_id))
    conn.commit()
    conn.close()
    return True

def get_poster_price() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'poster_price'")
    result = cursor.fetchone()
    conn.close()
    return int(result['setting_value']) if result else 10

def set_poster_price(price: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET setting_value = %s WHERE setting_key = 'poster_price'", (str(price),))
    conn.commit()
    conn.close()