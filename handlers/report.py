import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from services.report_service import get_report_data
from services.excel_service import generate_excel_report
from utils.logger import logger
from config import GROUP_CHAT_ID, REPORT_TOPIC_ID

def _get_safe_thread_id(topic_id):
    """Helper to safely convert Topic IDs to integers."""
    if topic_id and str(topic_id).strip().isdigit():
        return int(str(topic_id).strip())
    return None

def build_report_message(summary, orders, period_name):
    """Calculates exact metrics, separates delivery fees, and builds the HTML layout."""
    
    # 1. Safely calculate total Delivery Fees from the raw orders
    delivery_income = 0.0
    if orders:
        for o in orders:
            if isinstance(o, dict) and 'delivery_fee' in o:
                delivery_income += float(o['delivery_fee'])

    # 2. Subtract delivery from original sales to get pure Product Sales
    gross_sales = float(summary.get('sales', 0)) - delivery_income
    
    # 3. Pull other metrics
    manual_income = float(summary.get('income', 0))
    total_expenses = float(summary.get('expenses', 0))
    
    # 4. Calculate True Totals
    total_income = gross_sales + delivery_income + manual_income
    profit = total_income - total_expenses
    
    # We use bold HTML tags (<b>) instead of <pre> so text renders at full size
    return (
        "━━━━━━━━━━━━━━━━━━\n"
        f"<b>📊 REPORT ({period_name})</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Orders:</b> {summary.get('orders_count', 0)}\n"
        f"<b>Product Sales:</b> ${gross_sales:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"<b>Delivery Income:</b> ${delivery_income:.2f}\n"
        f"<b>Other Income:</b> ${manual_income:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"<b>TOTAL INCOME:</b> ${total_income:.2f}\n"
        f"<b>TOTAL EXPENSES:</b> ${total_expenses:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"<b>NET PROFIT:</b> ${profit:.2f}\n"
        "━━━━━━━━━━━━━━━━━━"
    )

async def send_report_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Today", callback_data="report_today"), InlineKeyboardButton("Yesterday", callback_data="report_yesterday")],
        [InlineKeyboardButton("This Week", callback_data="report_week"), InlineKeyboardButton("This Month", callback_data="report_month")],
        [InlineKeyboardButton("Custom Date", callback_data="report_custom")]
    ]
    await update.message.reply_text("Select a report period:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes clicks from the report menu."""
    query = update.callback_query
    data = query.data
    await query.answer()

    now = datetime.datetime.now()
    start_date, end_date, period_name = None, None, ""

    if data == "report_today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        period_name = "Today"
    elif data == "report_yesterday":
        yesterday = now - datetime.timedelta(days=1)
        start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        period_name = "Yesterday"
    elif data == "report_week":
        start_date = (now - datetime.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
        period_name = "This Week"
    elif data == "report_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - datetime.timedelta(seconds=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - datetime.timedelta(seconds=1)
        period_name = "This Month"
    elif data == "report_custom":
        await query.edit_message_text(
            "==============================\n"
            "Please copy the template below.\n"
            "Fill in the dates (YYYY-MM-DD).\n"
            "Then send it back.\n\n"
            "Start Date :\n"
            "End Date :\n"
            "=============================="
        )
        return

    await generate_and_send_report(update, context, start_date, end_date, period_name)

async def generate_and_send_report(update: Update, context: ContextTypes.DEFAULT_TYPE, start_date: datetime.datetime, end_date: datetime.datetime, period_name: str):
    """Fetches data, builds the text summary and Excel file, and sends them."""
    try:
        summary, orders, expenses, income = get_report_data(start_date, end_date)

        # Generate the new formatted message
        message = build_report_message(summary, orders, period_name)

        excel_stream = generate_excel_report(summary, orders, expenses, income)
        filename = f"Business_Report_{start_date.strftime('%Y-%m-%d')}.xlsx"

        # Send the file (works for both Callback queries and direct Text messages)
        target = update.callback_query.message if update.callback_query else update.message
        
        await target.reply_document(
            document=excel_stream,
            filename=filename,
            caption=message, 
            parse_mode='HTML' # parse_mode is now HTML, NO <pre> tags in the caption!
        )
        
    except Exception as e:
        logger.error(f"Report Generation Error: {e}")
        error_msg = "❌ Error generating report. Please check the logs."
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(error_msg)
        
        
async def send_daily_report_job(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled job to automatically generate and send the daily report."""
    try:
        now = datetime.datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        summary, orders, expenses, income = get_report_data(start_date, end_date)

        # Generate the new formatted message
        message = build_report_message(summary, orders, "AUTOMATIC DAILY")

        excel_stream = generate_excel_report(summary, orders, expenses, income)
        filename = f"Daily_Report_{start_date.strftime('%Y-%m-%d')}.xlsx"

        # Use context.bot to send messages without a user trigger
        await context.bot.send_document(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=_get_safe_thread_id(REPORT_TOPIC_ID),
            document=excel_stream,
            filename=filename,
            caption=message, 
            parse_mode='HTML' # parse_mode is now HTML, NO <pre> tags in the caption!
        )
        logger.info("Automatic daily report sent successfully.")
        
    except Exception as e:
        logger.error(f"Scheduled Report Error: {e}")