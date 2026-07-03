from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to the Order & Finance Bot!\n\n"
        "Available commands:\n"
        "/neworder - Create a new order\n"
        "/expense - Record a daily expense\n"
        "/expense_today - View today's expenses\n"
        "/earning_today - View today's earnings\n"
        "/help - Show this message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Use the menu commands to manage orders and finances. "
        "I will guide you through each process safely."
    )