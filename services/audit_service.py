import json
from typing import Dict, Any
from services.database_service import get_connection
from utils.logger import logger

def create_audit_table_if_not_exists() -> None:
    """Ensures the audit_logs table exists in MariaDB."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                table_name VARCHAR(50) NOT NULL,
                record_id INT NOT NULL,
                action VARCHAR(50) NOT NULL,
                updated_by VARCHAR(100) NOT NULL,
                old_data JSON NOT NULL,
                new_data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''')
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to create audit_logs table: {e}", exc_info=True)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def log_audit(table_name: str, record_id: int, action: str, updated_by: str, old_data: Dict[str, Any], new_data: Dict[str, Any], conn=None) -> None:
    """Records a JSON audit trail entry. Can accept an existing open database transaction connection."""
    logger.info(f"Audit Log -> Table: {table_name} | ID: {record_id} | Action: {action} | User: {updated_by}")
    
    # Clean non-serializable objects (like datetime) for JSON storage
    def clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = {}
        for k, v in d.items():
            if hasattr(v, 'isoformat'):
                cleaned[k] = v.isoformat()
            else:
                cleaned[k] = str(v) if v is not None else None
        return cleaned

    old_json = json.dumps(clean_dict(old_data))
    new_json = json.dumps(clean_dict(new_data))
    
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
        
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO audit_logs (table_name, record_id, action, updated_by, old_data, new_data)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (table_name, record_id, action, updated_by, old_json, new_json))
        if should_close:
            conn.commit()
    except Exception as e:
        logger.error(f"Audit log insertion failed: {e}", exc_info=True)
        if should_close:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if should_close:
            conn.close()