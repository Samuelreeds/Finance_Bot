import pymysql
from typing import List, Dict, Optional, Any
from services.database_service import get_connection

def soft_delete_record(table: str, record_id: int) -> bool:
    """Soft deletes a record by setting deleted_at to current timestamp."""
    allowed_tables = {'orders', 'expenses', 'income'}
    if table not in allowed_tables:
        raise ValueError("Invalid table name")
        
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = f"UPDATE `{table}` SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL"
            cursor.execute(sql, (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_paginated_records(table: str, page: int = 0, limit: int = 10, filter_today: bool = False) -> List[Dict[str, Any]]:
    """Retrieves paginated records ignoring soft-deleted items."""
    allowed_tables = {'orders', 'expenses', 'income'}
    if table not in allowed_tables:
        raise ValueError("Invalid table name")
        
    offset = page * limit
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            where_clause = "WHERE deleted_at IS NULL"
            if filter_today and table == 'orders':
                where_clause += " AND DATE(created_at) = CURDATE()"
                
            sql = f"SELECT * FROM `{table}` {where_clause} ORDER BY id DESC LIMIT %s OFFSET %s"
            cursor.execute(sql, (limit, offset))
            return cursor.fetchall()
    finally:
        conn.close()

def get_record_by_id(table: str, record_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single active record by ID."""
    allowed_tables = {'orders', 'expenses', 'income'}
    if table not in allowed_tables:
        raise ValueError("Invalid table name")
        
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = f"SELECT * FROM `{table}` WHERE id = %s AND deleted_at IS NULL"
            cursor.execute(sql, (record_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def update_order_record(order_id: int, customer_name: str, phone: str, address: str, product_id: int, quantity: int, delivery_date: str) -> Optional[Dict[str, Any]]:
    """Updates an order and recalculates financial fields using existing delivery fee."""
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Fetch product details for unit_price
            cursor.execute("SELECT product_name, unit_price FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            
            # Fetch current order to preserve the existing delivery_fee (which is based on the delivery option)
            cursor.execute("SELECT delivery_fee FROM orders WHERE id = %s", (order_id,))
            order = cursor.fetchone()
            
            if not product or not order:
                return None
                
            unit_price = product['unit_price']
            delivery_fee = order['delivery_fee']
            total_price = (unit_price * quantity) + delivery_fee
            
            sql = """
                UPDATE orders 
                SET customer_name = %s, phone = %s, address = %s, product_id = %s, 
                    quantity = %s, unit_price = %s, total_price = %s, delivery_date = %s
                WHERE id = %s AND deleted_at IS NULL
            """
            cursor.execute(sql, (customer_name, phone, address, product_id, quantity, unit_price, total_price, delivery_date, order_id))
        conn.commit()
        return get_record_by_id('orders', order_id)
    finally:
        conn.close()

def update_finance_record(table: str, record_id: int, amount: float, description: str, file_id: Optional[str] = None) -> bool:
    """Updates an expense or income record."""
    if table not in {'expenses', 'income'}:
        raise ValueError("Invalid table name")
        
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if file_id:
                sql = f"UPDATE `{table}` SET amount = %s, description = %s, telegram_file_id = %s WHERE id = %s AND deleted_at IS NULL"
                cursor.execute(sql, (amount, description, file_id, record_id))
            else:
                sql = f"UPDATE `{table}` SET amount = %s, description = %s WHERE id = %s AND deleted_at IS NULL"
                cursor.execute(sql, (amount, description, record_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_user_role(telegram_id: str) -> str:
    """Returns 'admin' or 'staff'. Defaults to 'staff' if unset."""
    conn = get_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT role FROM users WHERE telegram_id = %s", (str(telegram_id),))
            user = cursor.fetchone()
            return user['role'] if user else 'staff'
    finally:
        conn.close()