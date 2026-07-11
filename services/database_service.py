import os
import uuid
import pymysql
import datetime
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
from utils.logger import logger
from typing import Tuple, List, Dict, Any, Optional

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "nemdb")

def get_connection() -> pymysql.Connection:
    """Establishes and returns a new database connection."""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=DictCursor,
        autocommit=False
    )

def init_db() -> None:
    """Initializes database tables if they do not exist."""
    logger.info("Initializing database schema...")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                delivery_fee DECIMAL(10, 2) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_number VARCHAR(50) UNIQUE,
                customer_name VARCHAR(255) NOT NULL,
                phone VARCHAR(50) NOT NULL,
                address TEXT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                delivery_fee DECIMAL(10, 2) NOT NULL,
                delivery_method VARCHAR(30) DEFAULT 'Phnom Penh',
                total_price DECIMAL(10, 2) NOT NULL,
                delivery_date VARCHAR(100) NOT NULL,
                created_by VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                amount DECIMAL(10, 2) NOT NULL,
                description TEXT NOT NULL,
                telegram_file_id TEXT,
                created_by VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id INT AUTO_INCREMENT PRIMARY KEY,
                amount DECIMAL(10, 2) NOT NULL,
                description TEXT NOT NULL,
                telegram_file_id TEXT,
                created_by VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # NEW TABLE: Template-Based Poster Generation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poster_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(50) DEFAULT 'Food',
                template_name VARCHAR(100) NOT NULL,
                description VARCHAR(255),
                preview_image VARCHAR(255),
                prompt_template TEXT NOT NULL,
                status BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logger.info("Database initialization complete.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def save_order(customer_name: str, phone: str, address: str, product_id: int, quantity: int, unit_price: float, delivery_fee: float, total_price: float, delivery_date: str, created_by: str, delivery_method: str = "Phnom Penh") -> str:
    """Saves a new order and returns the generated order number safely."""
    logger.info("Saving new order to database...")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        temp_order_num = f"TEMP-{uuid.uuid4().hex[:8]}"
        
        cursor.execute('''
            INSERT INTO orders 
            (order_number, customer_name, phone, address, product_id, quantity, unit_price, delivery_fee, delivery_method, total_price, delivery_date, created_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (temp_order_num, customer_name, phone, address, product_id, quantity, unit_price, delivery_fee, delivery_method, total_price, delivery_date, created_by))
        
        inserted_id = cursor.lastrowid
        order_number = f"A{inserted_id:04d}"
        
        cursor.execute('UPDATE orders SET order_number = %s WHERE id = %s', (order_number, inserted_id))
        
        conn.commit()
        logger.info(f"Order {order_number} saved successfully.")
        return order_number
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving order: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def save_expense(amount: float, description: str, telegram_file_id: Optional[str], created_by: str) -> None:
    """Saves a new expense record."""
    logger.info("Saving new expense to database...")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO expenses (amount, description, telegram_file_id, created_by) 
            VALUES (%s, %s, %s, %s)
        ''', (amount, description, telegram_file_id, created_by))
        conn.commit()
        logger.info("Expense saved successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving expense: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def save_income(amount: float, description: str, telegram_file_id: Optional[str], created_by: str) -> None:
    """Saves a new manual income record."""
    logger.info("Saving new income to database...")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO income (amount, description, telegram_file_id, created_by) 
            VALUES (%s, %s, %s, %s)
        ''', (amount, description, telegram_file_id, created_by))
        conn.commit()
        logger.info("Income saved successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving income: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def get_report_data(start_date: datetime.datetime, end_date: datetime.datetime) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetches raw data and calculates exact summary metrics for the reporting engine."""
    logger.info(f"Fetching report data from {start_date} to {end_date}...")
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT o.*, p.product_name 
            FROM orders o 
            LEFT JOIN products p ON o.product_id = p.id 
            WHERE o.created_at >= %s AND o.created_at <= %s
        ''', (start_date, end_date))
        orders = cursor.fetchall()

        cursor.execute('SELECT * FROM expenses WHERE created_at >= %s AND created_at <= %s', (start_date, end_date))
        expenses = cursor.fetchall()

        cursor.execute('SELECT * FROM income WHERE created_at >= %s AND created_at <= %s', (start_date, end_date))
        income = cursor.fetchall()
        
        orders_count = len(orders)
        sales = sum(float(o.get('total_price', 0)) for o in orders) if orders else 0.0
        total_expenses = sum(float(e.get('amount', 0)) for e in expenses) if expenses else 0.0
        total_income = sum(float(i.get('amount', 0)) for i in income) if income else 0.0
        profit = total_income - total_expenses
        
        summary = {
            'orders_count': orders_count,
            'sales': sales,
            'expenses': total_expenses,
            'income': total_income,
            'profit': profit,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        logger.info("Report data fetched successfully.")
        return summary, orders, expenses, income
    except Exception as e:
        conn.rollback()
        logger.error(f"Error fetching report data: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()