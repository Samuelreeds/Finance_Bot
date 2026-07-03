from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from services.database_service import save_expense
from services.telegram_service import send_expense_to_group

AMOUNT, DESCRIPTION, CONFIRM = range(3)

async def expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.chat.type != 'private':
        await update.message.reply_text("Please send this command to me in a private chat to create a new record.")
        return ConversationHandler.END

    context.user_data.clear()
    
    user = update.effective_user
    context.user_data['staff_id'] = user.id
    context.user_data['staff_username'] = user.username or "N/A"
    context.user_data['staff_first_name'] = user.first_name or "Staff"

    await update.message.reply_text(
        "Let's record a new expense.\n"
        "What is the amount in USD? (Type /cancel to abort)",
        reply_markup=ReplyKeyboardRemove()
    )
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.replace('$', '').strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a positive number (e.g., 25.50):")
        return AMOUNT
        
    context.user_data['expense_amount'] = amount
    await update.message.reply_text("What is this expense for?")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Description cannot be empty. Please enter a valid description:")
        return DESCRIPTION
        
    context.user_data['expense_description'] = text
    amount = context.user_data['expense_amount']
    amount_str = f"{amount:g}" if amount % 1 == 0 else f"{amount:.2f}"
    
    preview = (
        "━━━━━━━━━━━━━━━━━━\n"
        "💵 Expense Preview\n"
        "Amount\n"
        f"${amount_str}\n"
        "Description\n"
        f"{context.user_data['expense_description']}\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    
    reply_keyboard = [['✅ Confirm', '❌ Cancel']]
    await update.message.reply_text(
        preview, 
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return CONFIRM

async def confirm_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text

    if answer == '✅ Confirm':
        amount = context.user_data['expense_amount']
        description = context.user_data['expense_description']
        
        save_expense(
            amount, 
            description, 
            context.user_data['staff_id'],
            context.user_data['staff_username'],
            context.user_data['staff_first_name']
        )
        
        # Optionally broadcast to group feed
        await send_expense_to_group(context, context.user_data)
        
        amount_str = f"{amount:g}" if amount % 1 == 0 else f"{amount:.2f}"
        await update.message.reply_text(
            f"✅ Expense Saved Successfully\nAmount: ${amount_str}\nDescription: {description}", 
            reply_markup=ReplyKeyboardRemove()
        )
        
    elif answer == '❌ Cancel':
        await update.message.reply_text("❌ Expense cancelled.", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Please choose '✅ Confirm' or '❌ Cancel'.")
        return CONFIRM
        
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Expense cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

expense_handler = ConversationHandler(
    entry_points=[CommandHandler('expense', expense)],
    states={
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        CONFIRM: [MessageHandler(filters.Regex('^(✅ Confirm|❌ Cancel)$'), confirm_expense)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)