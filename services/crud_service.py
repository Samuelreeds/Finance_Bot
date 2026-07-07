import time
import datetime
from typing import Optional, Dict, Any, List, Tuple
from services.database_service import get_connection
from utils.logger import logger

def get_today_orders(page: int = 0, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """Fetches paginated orders created today."""
    start_time = time.time()
    logger.info(f"DB Fetch: Today's Orders | Page: {page}")
    offset = page * limit
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM orders WHERE DATE(created_at) = %s", (today_str,))
        total_records = cursor.fetchone()['cnt']
        
        cursor.execute('''
            SELECT o.*, p.product_name 
            FROM orders o 
            LEFT JOIN products p ON o.product_id = p.id 
            WHERE DATE(o.created_at) = %s 
            ORDER BY o.id DESC LIMIT %s OFFSET %s
        ''', (today_str, limit, offset))
        records = cursor.fetchall()
        logger.info(f"DB Fetch complete in {time.time() - start_time:.4f}s | Found: {total_records}")
        return records, total_records
    except Exception as e:
        logger.error(f"Error fetching today orders: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single order by database ID with joined product details."""
    start_time = time.time()
    logger.info(f"DB Fetch: Order Details | ID: {order_id}")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT o.*, p.product_name 
            FROM orders o 
            LEFT JOIN products p ON o.product_id = p.id 
            WHERE o.id = %s
        ''', (order_id,))
        record = cursor.fetchone()
        logger.info(f"DB Fetch complete in {time.time() - start_time:.4f}s")
        return record
    except Exception as e:
        logger.error(f"Error fetching order ID {order_id}: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def get_today_expenses(page: int = 0, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """Fetches paginated expenses created today."""
    start_time = time.time()
    logger.info(f"DB Fetch: Today's Expenses | Page: {page}")
    offset = page * limit
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM expenses WHERE DATE(created_at) = %s", (today_str,))
        total_records = cursor.fetchone()['cnt']
        
        cursor.execute('''
            SELECT * FROM expenses 
            WHERE DATE(created_at) = %s 
            ORDER BY id DESC LIMIT %s OFFSET %s
        ''', (today_str, limit, offset))
        records = cursor.fetchall()
        logger.info(f"DB Fetch complete in {time.time() - start_time:.4f}s")
        return records, total_records
    except Exception as e:
        logger.error(f"Error fetching today expenses: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def get_expense_by_id(expense_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single expense record by ID."""
    start_time = time.time()
    logger.info(f"DB Fetch: Expense Details | ID: {expense_id}")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
        record = cursor.fetchone()
        logger.info(f"DB Fetch complete in {time.time() - start_time:.4f}s")
        return record
    except Exception as e:
        logger.error(f"Error fetching expense ID {expense_id}: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def get_today_income(page: int = 0, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """Fetches paginated income created today."""
    start_time = time.time()
    logger.info(f"DB Fetch: Today's Income | Page: {page}")
    offset = page * limit
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM income WHERE DATE(created_at) = %s", (today_str,))
        total_records = cursor.fetchone()['cnt']
        
        cursor.execute('''
            SELECT * FROM income 
            WHERE DATE(created_at) = %s 
            ORDER BY id DESC LIMIT %s OFFSET %s
        ''', (today_str, limit, offset))
        records = cursor.fetchall()
        logger.info(f"DB Fetch complete in {time.time() - start_time:.4f}s")
        return records, total_records
    except Exception as e:
        logger.error(f"Error fetching today income: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def get_income_by_id(income_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single income record by ID."""
    start_time = time.time()
    logger.info(f"DB Fetch: Income Details | ID: {income_id}")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM income WHERE id = %s", (income_id,))
        record = cursor.fetchone()
        logger.info(f"DB Fetch complete in {time.time() - start_time:.4f}s")
        return record
    except Exception as e:
        logger.error(f"Error fetching income ID {income_id}: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()