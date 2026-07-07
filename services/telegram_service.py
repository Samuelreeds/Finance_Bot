import os
import datetime
from telegram import InputMediaPhoto
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
ORDER_TOPIC_ID = os.getenv("ORDER_TOPIC_ID")
FINANCE_TOPIC_ID = os.getenv("FINANCE_TOPIC_ID")

def _get_safe_thread_id(topic_id: str | None) -> int | None:
    if topic_id and str(topic_id).strip().isdigit():
        return int(str(topic_id).strip())
    return None

def format_order_message(order_data: dict, is_update: bool = False, changed_by: str = "") -> str:
    """Formats the order dictionary to match the group layout with A-prefix."""
    # Logic to handle A prefix: if it's a number, format as 'A' + number
    raw_id = order_data.get('order_number', '0000')
    order_id = f"A{str(raw_id).replace('A', '')}" 
    
    customer = order_data['customer_name']
    product = order_data.get('product_name', 'Product')
    qty = order_data['quantity']
    delivery_fee = float(order_data['delivery_fee'])
    total = float(order_data['total_price'])
    delivery_date = order_data['delivery_date']
    address = order_data['address']
    phone = order_data['phone']

    if is_update:
        dt_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        return (
            f"✏️ <b>UPDATED:</b> {order_id}/ {customer}\n"
            f"{product}\n"
            f"ចំនួន {qty} ឈុត\n"
            f"Delivery ({delivery_fee:g}$)\n"
            f"Total = {total:g}$\n"
            f"ថ្ងៃដឹក : {delivery_date}\n"
            f"ទីតាំង : {address}\n"
            f"<code>{phone}</code>\n"
            f"<i>(Edited by {changed_by} at {dt_str})</i>"
        )

    return (
        f"{order_id}/ {customer}\n"
        f"{product}\n"
        f"ចំនួន {qty} ឈុត\n"
        f"Delivery ({delivery_fee:g}$)\n"
        f"Total = {total:g}$\n"
        f"ថ្ងៃដឹក : {delivery_date}\n"
        f"ទីតាំង : {address}\n"
        f"<code>{phone}</code>"
    )
async def send_order_to_group(context: ContextTypes.DEFAULT_TYPE, order_data: dict, is_update: bool = False, changed_by: str = "") -> None:
    """Sends the order to the Telegram group asynchronously."""
    logger.info("Transmitting order to group chat...")
    if not GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID not configured.")
        return
        
    message = format_order_message(order_data, is_update, changed_by)
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=_get_safe_thread_id(ORDER_TOPIC_ID),
            text=message,
            parse_mode='HTML'
        )
        logger.info("Order message dispatched successfully.")
    except Exception as e:
        logger.error(f"Failed to send order message: {e}", exc_info=True)

async def send_finance_to_group(context: ContextTypes.DEFAULT_TYPE, draft: dict, is_income: bool, is_update: bool = False, changed_by: str = "") -> None:
    """Sends the finance record (supporting single or multiple images as an album) to the Telegram group."""
    logger.info("Transmitting finance record to group chat...")
    if not GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID not configured.")
        return

    thread_id = _get_safe_thread_id(FINANCE_TOPIC_ID)
    if is_update:
        title = "INCOME UPDATED" if is_income else "EXPENSE UPDATED"
        dt_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        message = (
            f"━━━━━━━━━━━━━━━━━━\n<b>{title}</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"<b>Updated By:</b> {changed_by}\n<b>Updated At:</b> {dt_str}\n━━━━━━━━━━━━━━━━━━\n"
            f"<b>Amount:</b> ${float(draft['amount']):.2f}\n<b>Description:</b> {draft['description']}\n"
            f"<b>Logged By:</b> {draft.get('created_by', changed_by)}\n━━━━━━━━━━━━━━━━━━"
        )
    else:
        title = "NEW INCOME RECORD" if is_income else "NEW EXPENSE RECORD"
        message = (
            f"<pre>==============================\n{title.center(30)}\n==============================\n"
            f"Amount      : ${draft['amount']:.2f}\nDescription : {draft['description']}\n"
            f"Created By  : {draft['created_by']}\n==============================</pre>"
        )
    
    file_id_string = draft.get('telegram_file_id')
    try:
        if file_id_string:
            file_ids = [fid.strip() for fid in file_id_string.split(",") if fid.strip()]
            if len(file_ids) == 1:
                await context.bot.send_photo(chat_id=GROUP_CHAT_ID, message_thread_id=thread_id, photo=file_ids[0], caption=message, parse_mode='HTML')
            elif len(file_ids) > 1:
                media_group = [InputMediaPhoto(media=fid, caption=message if idx == 0 else None, parse_mode='HTML') for idx, fid in enumerate(file_ids)]
                await context.bot.send_media_group(chat_id=GROUP_CHAT_ID, message_thread_id=thread_id, media=media_group)
        else:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, message_thread_id=thread_id, text=message, parse_mode='HTML')
        logger.info("Finance record dispatched successfully.")
    except Exception as e:
        logger.error(f"Failed to send finance message: {e}", exc_info=True)