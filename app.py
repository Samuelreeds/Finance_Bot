import os
import datetime
from dotenv import load_dotenv
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Load environment variables
load_dotenv()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Configuration & Setup
from handlers.product_admin import product_admin_handler
from config import BOT_TOKEN
from services.database_service import init_db
from utils.logger import logger

# Module Handlers
from handlers.template_handler import send_main_menu, handle_input, handle_callback
from handlers.product_admin import clear_data_command
from handlers.report import handle_report_callback, send_daily_report_job 
from handlers.poster import add_tokens_handler, set_poster_price_handler, balance_handler, prompts_handler, poster_history_handler
from handlers.poster_flow import poster_conv_handler

async def post_init(application: Application):
    """Sets the Telegram bot menu commands on startup based on user roles."""
    
    # 1. Standard commands visible to EVERYONE (Default Public Scope)
    public_commands = [
        BotCommand("start", "🏠 Open Main Menu"),
        BotCommand("balance", "🪙 Check Token Balance"),
    ]
    await application.bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())

    # 2. Admin commands appended and visible ONLY to your specific Admin Chat ID
    if ADMIN_CHAT_ID:
        admin_commands = public_commands + [
            BotCommand("products", "⚙️ Manage products (Admin)"),
            BotCommand("prompts", "📝 Manage Prompts (Admin)"),
            BotCommand("posterhistory", "📜 View Poster History (Admin)"),
        ]
        try:
            await application.bot.set_my_commands(
                admin_commands, 
                scope=BotCommandScopeChat(chat_id=int(ADMIN_CHAT_ID))
            )
            logger.info(f"Admin command menu scoped successfully for ID: {ADMIN_CHAT_ID}")
        except Exception as e:
            logger.error(f"Could not set admin command scope for {ADMIN_CHAT_ID}: {e}")

def main():
    """Main application loop."""
    # Ensure database schemas are updated
    init_db()
    logger.info("Starting bot...")
    
    # Initialize the Application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # --- ⏰ SCHEDULED JOBS ---
    # Sends the daily report to the group at exactly 23:55 (11:55 PM) everyday.
    target_time = datetime.time(hour=23, minute=55, second=0)
    application.job_queue.run_daily(send_daily_report_job, time=target_time)

    # --- 🛠 COMMAND HANDLERS ---
    application.add_handler(CommandHandler("start", send_main_menu))
    application.add_handler(product_admin_handler) 
    application.add_handler(poster_conv_handler)
    
    # AI Poster Admin Commands
    application.add_handler(CommandHandler("addtokens", add_tokens_handler))
    application.add_handler(CommandHandler("setposterprice", set_poster_price_handler))
    application.add_handler(CommandHandler("balance", balance_handler))
    application.add_handler(CommandHandler("prompts", prompts_handler))
    application.add_handler(CommandHandler("posterhistory", poster_history_handler))
    application.add_handler(CommandHandler("cleardata", clear_data_command))

    # --- 📨 MESSAGE HANDLER (The Engine) ---
    # Listens for all text templates and photo uploads
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_input))
    
    # --- 🔘 CALLBACK QUERY HANDLERS (Inline Buttons) ---
    # Catch report buttons FIRST using Regex pattern
    application.add_handler(CallbackQueryHandler(handle_report_callback, pattern='^report_'))
    # Catch all other buttons (Confirm, Cancel, Poster styles)
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()