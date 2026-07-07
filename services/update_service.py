import time
from typing import Dict, Any
from services.database_service import get_connection
from services.audit_service import log_audit
from utils.logger import logger

def update_order(record_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any], updated_by: str) -> None:
    """Updates only modified order fields, automatically recalibrating totals and creating an audit record."""
    start_time = time.time()
    logger.info(f"DB Update: Order ID {record_id} | User: {updated_by}")
    
    # Isolate modified fields only
    fields_to_update = {}
    for key, val in new_data.items():
        if key in old_data and str(old_data[key]) != str(val):
            fields_to_update[key] = val
            
    if not fields_to_update:
        logger.info("No field modifications detected. Skipping DB execution.")
        return

    # Map Python domain keys to MariaDB column names
    col_map = {
        'customer_name': 'customer_name',
        'phone': 'phone',
        'address': 'address',
        'product_id': 'product_id',
        'quantity': 'quantity',
        'unit_price': 'unit_price',
        'delivery_fee': 'delivery_fee',
        'total_price': 'total_price',
        'delivery_date': 'delivery_date',
        'status': 'status'
    }

    set_clauses = []
    params = []
    for key, val in fields_to_update.items():
        if key in col_map:
            set_clauses.append(f"{col_map[key]} = %s")
            params.append(val)
            
    params.append(record_id)
    sql = f"UPDATE orders SET {', '.join(set_clauses)} WHERE id = %s"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        logger.info(f"Executing SQL: {sql} | Params: {params}")
        cursor.execute(sql, tuple(params))
        log_audit('orders', record_id, 'UPDATE', updated_by, old_data, new_data, conn=conn)
        conn.commit()
        logger.info(f"Order {record_id} updated successfully in {time.time() - start_time:.4f}s")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update order ID {record_id}: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def update_expense(record_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any], updated_by: str) -> None:
    """Updates modified expense fields and records audit log."""
    start_time = time.time()
    logger.info(f"DB Update: Expense ID {record_id} | User: {updated_by}")
    
    fields_to_update = {}
    for key in ['amount', 'description', 'telegram_file_id']:
        if key in new_data and str(old_data.get(key)) != str(new_data[key]):
            fields_to_update[key] = new_data[key]
            
    if not fields_to_update:
        return

    set_clauses = [f"{k} = %s" for k in fields_to_update.keys()]
    params = list(fields_to_update.values()) + [record_id]
    sql = f"UPDATE expenses SET {', '.join(set_clauses)} WHERE id = %s"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, tuple(params))
        log_audit('expenses', record_id, 'UPDATE', updated_by, old_data, new_data, conn=conn)
        conn.commit()
        logger.info(f"Expense {record_id} updated successfully in {time.time() - start_time:.4f}s")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update expense ID {record_id}: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def update_income(record_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any], updated_by: str) -> None:
    """Updates modified income fields and records audit log."""
    start_time = time.time()
    logger.info(f"DB Update: Income ID {record_id} | User: {updated_by}")
    
    fields_to_update = {}
    for key in ['amount', 'description', 'telegram_file_id']:
        if key in new_data and str(old_data.get(key)) != str(new_data[key]):
            fields_to_update[key] = new_data[key]
            
    if not fields_to_update:
        return

    set_clauses = [f"{k} = %s" for k in fields_to_update.keys()]
    params = list(fields_to_update.values()) + [record_id]
    sql = f"UPDATE income SET {', '.join(set_clauses)} WHERE id = %s"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, tuple(params))
        log_audit('income', record_id, 'UPDATE', updated_by, old_data, new_data, conn=conn)
        conn.commit()
        logger.info(f"Income {record_id} updated successfully in {time.time() - start_time:.4f}s")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update income ID {record_id}: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()