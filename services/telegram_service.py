import datetime
from config import GROUP_CHAT_ID, ORDER_TOPIC_ID, EXPENSE_TOPIC_ID, INCOME_TOPIC_ID

def _get_safe_thread_id(topic_id):
    """Helper to safely convert Topic IDs to integers without crashing the bot."""
    if topic_id and str(topic_id).strip().isdigit():
        return int(str(topic_id).strip())
    return None

def format_order_message(order_data):
    """Formats the order data into the detailed business template (used for Preview)."""
    order_num = order_data.get('order_number', 'PREVIEW')
    header = "ORDER PREVIEW" if order_num == 'PREVIEW' else f"ORDER {order_num.replace('#', 'A')}"
    
    unit_price = f"${order_data['unit_price']:.2f}"
    delivery = f"${order_data['delivery_fee']:.2f}"
    total = f"${order_data['total_price']:.2f}"
    
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    created_by = order_data.get('created_by', 'Staff')

    # We use bold HTML tags instead of <pre> so Khmer text renders at full size
    return (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{header}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Customer:</b> {order_data['customer_name']}\n"
        f"<b>Phone Number:</b> {order_data['phone']}\n"
        f"<b>Address:</b> {order_data['address']}\n"
        f"<b>Product:</b> {order_data['product_name']}\n"
        f"<b>Quantity:</b> {order_data['quantity']}\n"
        f"<b>Unit Price:</b> {unit_price}\n"
        f"<b>Delivery Fee:</b> {delivery}\n"
        "────────────────────────────\n"
        f"<b>TOTAL:</b> {total}\n"
        "────────────────────────────\n"
        f"<b>Delivery Date:</b> {order_data['delivery_date']}\n"
        f"<b>Created By:</b> {created_by}\n"
        f"<b>Time:</b> {created_at}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

async def send_order_to_group(context, order_data):
    """Sends the compact Khmer template to the main Telegram group."""
    delivery = order_data['delivery_fee']
    total = order_data['total_price']
    
    # Format numbers to drop the .00 if they are whole numbers (e.g., $2 instead of $2.00)
    delivery_str = f"{delivery:g}" if delivery % 1 == 0 else f"{delivery:.2f}"
    total_str = f"{total:g}" if total % 1 == 0 else f"{total:.2f}"
    
    order_number = order_data['order_number'].replace('#', 'A')
    created_by = order_data.get('created_by', 'Staff')

    # The exact format from your screenshot, plus the staff member's name
    compact_message = (
        f"{order_number}/ {order_data['customer_name']}\n"
        f"{order_data['product_name']}\n"
        f"ចំនួន {order_data['quantity']} ឈុត\n"
        f"Delivery ({delivery_str}$)\n"
        f"Total = {total_str}$\n"
        f"ថ្ងៃដឹក : {order_data['delivery_date']}\n"
        f"ទីតាំង : {order_data['address']}\n"
        f"{order_data['phone']}\n"
        f"Created By : {created_by}"
    )
    
    # Send as normal text (no <pre> tags) to match the screenshot and route to the Order Topic
    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID, 
        message_thread_id=_get_safe_thread_id(ORDER_TOPIC_ID),
        text=compact_message
    )

async def send_finance_to_group(context, finance_data, is_income=False):
    """Sends income/expense records to the group without shrinking Khmer descriptions."""
    title = "INCOME" if is_income else "EXPENSE"
    topic_id = INCOME_TOPIC_ID if is_income else EXPENSE_TOPIC_ID
    
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    created_by = finance_data.get('created_by', 'Staff')
    
    # Formatted with HTML bolding to prevent Khmer script shrinking
    message = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{title} RECORD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Amount:</b> ${finance_data['amount']:.2f}\n"
        f"<b>Description:</b> {finance_data['description']}\n"
        "────────────────────────────\n"
        f"<b>Created By:</b> {created_by}\n"
        f"<b>Time:</b> {created_at}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    thread_id = _get_safe_thread_id(topic_id)
    
    if finance_data.get('telegram_file_id'):
        await context.bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=thread_id,
            photo=finance_data['telegram_file_id'],
            caption=message,
            parse_mode='HTML'
        )
    else:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=thread_id,
            text=message,
            parse_mode='HTML'
        )