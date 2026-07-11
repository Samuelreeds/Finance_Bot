import pymysql
from services.database_service import get_connection

def get_food_templates():
    """Fetch active food templates from the database."""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT id, template_name, description, preview_image, prompt_template 
            FROM poster_templates 
            WHERE category = 'Food' AND status = TRUE
        ''')
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_template_by_id(template_id):
    """Fetch a specific template by ID."""
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute('SELECT * FROM poster_templates WHERE id = %s', (template_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()