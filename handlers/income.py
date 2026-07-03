from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from services.database_service import get_today_order_income

async def income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count, total = get_today_order_income()
    
    message = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 Today's Income\n"
        f"📦 Total Orders: {count}\n"
        f"💵 Revenue: ${total:.2f}\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    
    await update.message.reply_text(message)

# Simplified to a basic CommandHandler
income_handler = CommandHandler('income', income)