import time
from typing import List, Dict, Any, Tuple
from services.database_service import get_connection
from utils.logger import logger

def search_orders(query: str, page: int = 0, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """Searches orders by order_number, customer_name, or phone using partial matching."""
    start_time = time.time()
    logger.info(f"DB Search: Orders | Query: '{query}' | Page: {page}")
    offset = page * limit
    search_term = f"%{query.strip()}%"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql_count = '''
            SELECT COUNT(*) as cnt FROM orders 
            WHERE order_number LIKE %s OR customer_name LIKE %s OR phone LIKE %s
        '''
        cursor.execute(sql_count, (search_term, search_term, search_term))
        total_records = cursor.fetchone()['cnt']
        
        sql_fetch = '''
            SELECT o.*, p.product_name 
            FROM orders o 
            LEFT JOIN products p ON o.product_id = p.id 
            WHERE o.order_number LIKE %s OR o.customer_name LIKE %s OR o.phone LIKE %s 
            ORDER BY o.id DESC LIMIT %s OFFSET %s
        '''
        cursor.execute(sql_fetch, (search_term, search_term, search_term, limit, offset))
        records = cursor.fetchall()
        logger.info(f"DB Search complete in {time.time() - start_time:.4f}s | Found: {total_records}")
        return records, total_records
    except Exception as e:
        logger.error(f"Error searching orders: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def search_expenses(query: str, page: int = 0, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """Searches expenses by description or created_by using partial matching."""
    start_time = time.time()
    logger.info(f"DB Search: Expenses | Query: '{query}' | Page: {page}")
    offset = page * limit
    search_term = f"%{query.strip()}%"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql_count = "SELECT COUNT(*) as cnt FROM expenses WHERE description LIKE %s OR created_by LIKE %s"
        cursor.execute(sql_count, (search_term, search_term))
        total_records = cursor.fetchone()['cnt']
        
        sql_fetch = '''
            SELECT * FROM expenses 
            WHERE description LIKE %s OR created_by LIKE %s 
            ORDER BY id DESC LIMIT %s OFFSET %s
        '''
        cursor.execute(sql_fetch, (search_term, search_term, limit, offset))
        records = cursor.fetchall()
        logger.info(f"DB Search complete in {time.time() - start_time:.4f}s | Found: {total_records}")
        return records, total_records
    except Exception as e:
        logger.error(f"Error searching expenses: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def search_income(query: str, page: int = 0, limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """Searches income by description or created_by using partial matching."""
    start_time = time.time()
    logger.info(f"DB Search: Income | Query: '{query}' | Page: {page}")
    offset = page * limit
    search_term = f"%{query.strip()}%"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql_count = "SELECT COUNT(*) as cnt FROM income WHERE description LIKE %s OR created_by LIKE %s"
        cursor.execute(sql_count, (search_term, search_term))
        total_records = cursor.fetchone()['cnt']
        
        sql_fetch = '''
            SELECT * FROM income 
            WHERE description LIKE %s OR created_by LIKE %s 
            ORDER BY id DESC LIMIT %s OFFSET %s
        '''
        cursor.execute(sql_fetch, (search_term, search_term, limit, offset))
        records = cursor.fetchall()
        logger.info(f"DB Search complete in {time.time() - start_time:.4f}s | Found: {total_records}")
        return records, total_records
    except Exception as e:
        logger.error(f"Error searching income: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()