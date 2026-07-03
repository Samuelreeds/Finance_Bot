from services.database_service import get_connection

def get_active_prompts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, prompt FROM poster_prompts WHERE active = 1")
    results = cursor.fetchall()
    conn.close()
    return results

def get_all_prompts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, active FROM poster_prompts")
    results = cursor.fetchall()
    conn.close()
    return results

def get_prompt_by_id(prompt_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM poster_prompts WHERE id = %s", (prompt_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def add_prompt(name: str, prompt: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO poster_prompts (name, prompt) VALUES (%s, %s)", (name, prompt))
    conn.commit()
    conn.close()

def toggle_prompt(prompt_id: int, active: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE poster_prompts SET active = %s WHERE id = %s", (active, prompt_id))
    conn.commit()
    conn.close()