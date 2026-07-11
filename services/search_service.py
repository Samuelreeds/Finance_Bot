import pymysql
from services.database_service import get_connection
from typing import Tuple, List, Dict, Any

def _execute_search(table: str, search_query: str, page: int, limit: int, fields: list) -> Tuple[List[Dict[str, Any]], int]:
    offset = page * limit
    search_term = f"%{search_query}%"
    
    where_clauses = " OR ".join([f"{field} LIKE %s" for field in fields])
    params = [search_term] * len(fields)
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as total FROM `{table}` WHERE {where_clauses}", params)
            total = cursor.fetchone()['total']
            
            cursor.execute(f"SELECT * FROM `{table}` WHERE {where_clauses} ORDER BY id DESC LIMIT %s OFFSET %s", params + [limit, offset])
            records = cursor.fetchall()
            
            return records, total
    finally:
        conn.close()

def search_orders(query: str, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    return _execute_search('orders', query, page, limit, ['order_number', 'customer_name', 'phone'])

def search_expenses(query: str, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    return _execute_search('expenses', query, page, limit, ['description'])

def search_income(query: str, page: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    return _execute_search('income', query, page, limit, ['description'])