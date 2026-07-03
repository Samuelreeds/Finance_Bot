import datetime
from services.database_service import get_connection

def get_report_data(start_date: datetime.datetime, end_date: datetime.datetime):
    """Fetches raw data and calculates the summary for the given date range."""
    conn = get_connection()
    cursor = conn.cursor()

    # Join orders with products to get the product_name for the Excel export
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

    conn.close()

    # Calculate metrics (Default to 0.0 if empty)
    orders_count = len(orders)
    sales = sum(float(o['total_price']) for o in orders) if orders else 0.0
    total_expenses = sum(float(e['amount']) for e in expenses) if expenses else 0.0
    total_income = sum(float(i['amount']) for i in income) if income else 0.0
    
    # As explicitly defined: Profit = Income - Expenses
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

    return summary, orders, expenses, income