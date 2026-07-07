import os
import datetime
from datetime import timezone
from dotenv import load_dotenv
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

from handlers.product_admin import product_admin_handler, clear_data_command
from config import BOT_TOKEN
from services.database_service import init_db
from services.audit_service import create_audit_table_if_not_exists
from utils.logger import logger
from handlers.template_handler import send_main_menu, handle_input, handle_callback
from handlers.report import handle_report_callback, send_daily_report_job 
from handlers.poster import add_tokens_handler, set_poster_price_handler, balance_handler, prompts_handler, poster_history_handler
from handlers.poster_flow import poster_conv_handler
from handlers.manage_handler import (
    handle_manage_callback, 
    view_order_command, 
    view_expense_command, 
    view_income_command
)
from handlers.edit_handler import handle_edit_callback

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception handled centrally:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("⚠️ An unexpected internal error occurred. Administrators have been notified.")
        except Exception:
            pass

async def catch_all_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    logger.warning(f"Unhandled Callback Detected: {query.data}")
    await query.answer("⚠️ Action unavailable or not routed properly.")

async def post_init(application: Application) -> None:
    public_commands = [
        BotCommand("start", "🏠 Open Main Menu"),
        BotCommand("balance", "🪙 Check Token Balance"),
    ]
    await application.bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())

    if ADMIN_CHAT_ID:
        admin_commands = public_commands + [
            BotCommand("products", "⚙️ Manage products (Admin)"),
            BotCommand("prompts", "📝 Manage Prompts (Admin)"),
            BotCommand("posterhistory", "📜 View Poster History (Admin)"),
        ]
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=int(ADMIN_CHAT_ID)))
            logger.info("Admin commands registered.")
        except Exception as e:
            logger.error(f"Admin command scope error: {e}")

def main() -> None:
    init_db()
    create_audit_table_if_not_exists()
    logger.info("Database and audit schemas verified. Starting application...")
    
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_error_handler(error_handler)

    cam_tz = timezone(datetime.timedelta(hours=7))
    target_time = datetime.time(hour=23, minute=58, second=0, tzinfo=cam_tz)
    application.job_queue.run_daily(send_daily_report_job, time=target_time)

    # --- GROUP 0: CALLBACK QUERY ROUTERS ---
    application.add_handler(CallbackQueryHandler(handle_report_callback, pattern='^report_'), group=0)
    application.add_handler(CallbackQueryHandler(handle_manage_callback, pattern='^manage_'), group=0)
    application.add_handler(CallbackQueryHandler(handle_edit_callback, pattern='^edit_'), group=0)
    application.add_handler(CallbackQueryHandler(handle_callback, pattern='^selprod_'), group=0)
    application.add_handler(CallbackQueryHandler(handle_callback, pattern='^(pstyle_|poster_)'), group=0)
    application.add_handler(CallbackQueryHandler(handle_callback, pattern='^(confirm|cancel)$'), group=0)
    application.add_handler(CallbackQueryHandler(catch_all_callbacks), group=0)

    # --- GROUP 1: COMMANDS & CONVERSATIONS ---
    application.add_handler(CommandHandler("start", send_main_menu), group=1)
    application.add_handler(product_admin_handler, group=1) 
    application.add_handler(poster_conv_handler, group=1)
    
    # Deep-link View Handlers for CRUD Module
    application.add_handler(MessageHandler(filters.Regex(r"^/view_order_\d+$"), view_order_command), group=1)
    application.add_handler(MessageHandler(filters.Regex(r"^/view_exp_\d+$"), view_expense_command), group=1)
    application.add_handler(MessageHandler(filters.Regex(r"^/view_inc_\d+$"), view_income_command), group=1)
    
    application.add_handler(CommandHandler("addtokens", add_tokens_handler), group=1)
    application.add_handler(CommandHandler("setposterprice", set_poster_price_handler), group=1)
    application.add_handler(CommandHandler("balance", balance_handler), group=1)
    application.add_handler(CommandHandler("prompts", prompts_handler), group=1)
    application.add_handler(CommandHandler("posterhistory", poster_history_handler), group=1)
    application.add_handler(CommandHandler("cleardata", clear_data_command), group=1)

    # --- GROUP 2: GENERAL TEXT/PHOTO PROCESSING ---
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_input), group=2)
    
    logger.info("Bot is active and polling.")
    application.run_polling()

if __name__ == "__main__":
    main()