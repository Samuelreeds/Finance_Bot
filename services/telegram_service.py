import os
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

def format_order_message(draft: dict) -> str:
    order_num = draft.get('order_number', 'A0000')
    customer = draft.get('customer_name', '')
    product = draft.get('product_name', '')
    qty = draft.get('quantity', 0)
    delivery = draft.get('delivery_fee', 0)
    total = draft.get('total_price', 0)
    date = draft.get('delivery_date', '')
    address = draft.get('address', '')
    phone = draft.get('phone', '')

    # :g removes the trailing .0 from decimals (e.g., 2.0 becomes 2)
    return (
        f"{order_num}/ {customer}\n"
        f"{product}\n"
        f"ចំនួន {qty} ឈុត\n"
        f"Delivery ({delivery:g}$)\n"
        f"Total = {total:g}$\n"
        f"ថ្ងៃដឹក : {date}\n"
        f"ទីតាំង : {address}\n"
        f"{phone}"
    )
async def send_order_to_group(context: ContextTypes.DEFAULT_TYPE, order_data: dict) -> None:
    """Sends the confirmed order to the Telegram group asynchronously."""
    logger.info("Sending order to group chat...")
    if not GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID not configured.")
        return
        
    message = format_order_message(order_data)
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=_get_safe_thread_id(ORDER_TOPIC_ID),
            text=message,
            parse_mode=None
        )
        logger.info("Order message dispatched successfully.")
    except Exception as e:
        logger.error(f"Failed to send order message: {e}", exc_info=True)

async def send_finance_to_group(context: ContextTypes.DEFAULT_TYPE, draft: dict, is_income: bool) -> None:
    """Sends the confirmed finance record (supporting single or multiple images as an album) to the Telegram group."""
    logger.info("Sending finance record to group chat...")
    if not GROUP_CHAT_ID:
        logger.warning("GROUP_CHAT_ID not configured.")
        return

    title = "NEW INCOME RECORD" if is_income else "NEW EXPENSE RECORD"
    message = (
        f"<pre>"
        f"==============================\n"
        f"{title.center(30)}\n"
        f"==============================\n"
        f"Amount      : ${draft['amount']:.2f}\n"
        f"Description : {draft['description']}\n"
        f"Created By  : {draft['created_by']}\n"
        f"=============================="
        f"</pre>"
    )
    
    thread_id = _get_safe_thread_id(FINANCE_TOPIC_ID)
    file_id_string = draft.get('telegram_file_id')

    try:
        if file_id_string:
            file_ids = [fid.strip() for fid in file_id_string.split(",") if fid.strip()]
            
            if len(file_ids) == 1:
                await context.bot.send_photo(
                    chat_id=GROUP_CHAT_ID,
                    message_thread_id=thread_id,
                    photo=file_ids[0],
                    caption=message,
                    parse_mode='HTML'
                )
            elif len(file_ids) > 1:
                media_group = []
                for index, fid in enumerate(file_ids):
                    if index == 0:
                        media_group.append(InputMediaPhoto(media=fid, caption=message, parse_mode='HTML'))
                    else:
                        media_group.append(InputMediaPhoto(media=fid))
                
                await context.bot.send_media_group(
                    chat_id=GROUP_CHAT_ID,
                    message_thread_id=thread_id,
                    media=media_group
                )
        else:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=thread_id,
                text=message,
                parse_mode='HTML'
            )
        logger.info("Finance record dispatched successfully.")
    except Exception as e:
        logger.error(f"Failed to send finance message: {e}", exc_info=True)