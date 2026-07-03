import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from services.product_service import get_active_products, get_product_by_id, update_product_price
from dotenv import load_dotenv

load_dotenv()
ADMIN_CHAT_ID = str(os.getenv("ADMIN_CHAT_ID"))

WAITING_FOR_PRICE = range(1)

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized. This area is restricted to administrators.")
        return ConversationHandler.END

    if update.message.chat.type != 'private':
        await update.message.reply_text("Please manage products in a private chat.")
        return ConversationHandler.END

    products = get_active_products()
    if not products:
        await update.message.reply_text("No active products found in the database.")
        return ConversationHandler.END

    text = "📦 *Product List*\n"
    keyboard = []
    
    for i, p in enumerate(products, 1):
        unit_str = f"{p['unit_price']:g}" if p['unit_price'] % 1 == 0 else f"{p['unit_price']:.2f}"
        text += f"{i}️⃣ {p['product_name']} — ${unit_str}\n"
        keyboard.append([InlineKeyboardButton(f"✏️ Edit {p['product_name']}", callback_data=f"editprice_{p['id']}")])

    await update.message.reply_text(
        text, 
        parse_mode='Markdown', 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

async def edit_price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split('_')[1])
    product = get_product_by_id(product_id)

    if not product:
        await query.edit_message_text("❌ Product not found.")
        return ConversationHandler.END

    context.user_data['edit_product_id'] = product_id
    context.user_data['edit_product_name'] = product['product_name']

    await query.edit_message_text(
        f"✏️ *Editing {product['product_name']}*\n\nEnter the new unit price:", 
        parse_mode='Markdown'
    )
    return WAITING_FOR_PRICE

async def receive_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_price = float(update.message.text.strip())
        if new_price < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Please enter a valid positive number.")
        return WAITING_FOR_PRICE

    product_id = context.user_data['edit_product_id']
    product_name = context.user_data['edit_product_name']

    # Update database
    update_product_price(product_id, new_price)

    new_str = f"{new_price:g}" if new_price % 1 == 0 else f"{new_price:.2f}"
    await update.message.reply_text(
        f"✅ *{product_name}* unit price successfully updated to *${new_str}*.", 
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Edit cancelled.")
    return ConversationHandler.END

product_admin_handler = ConversationHandler(
    entry_points=[
        CommandHandler('products', list_products),
        CallbackQueryHandler(edit_price_callback, pattern='^editprice_')
    ],
    states={
        WAITING_FOR_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_price)]
    },
    fallbacks=[CommandHandler('cancel', cancel_admin)]
)

async def clear_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to wipe test data from your exact nemdb tables."""
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return

    from services.database_service import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # We target ONLY your exact transaction tables from nemdb
        target_tables = ['orders', 'expenses', 'income', 'poster_history']
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        for table in target_tables:
            cursor.execute(f"TRUNCATE TABLE {table};")
                
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        
        await update.message.reply_text(
            "✅ <b>ALL TEST DATA CLEARED!</b>\n\n"
            "• <code>orders</code> -> Reset to 0\n"
            "• <code>expenses</code> -> Reset to 0\n"
            "• <code>income</code> -> Reset to 0\n"
            "• <code>poster_history</code> -> Reset to 0\n\n"
            "All new order numbers will now start fresh at #1!",
            parse_mode='HTML'
        )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Database error: {e}")
    finally:
        conn.close()