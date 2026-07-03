from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from services.database_service import save_order
from services.telegram_service import send_order_to_group
from services.product_service import get_active_products, get_product_by_name

NAME, PHONE, ADDRESS, PRODUCT, QUANTITY, DISPATCH_DATE, CONFIRM = range(7)

async def neworder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.chat.type != 'private':
        await update.message.reply_text("Please send this command to me in a private chat to create a new record.")
        return ConversationHandler.END

    context.user_data.clear()
    
    user = update.effective_user
    context.user_data['staff_id'] = user.id
    context.user_data['staff_username'] = user.username or "N/A"
    context.user_data['staff_first_name'] = user.first_name or "Staff"

    await update.message.reply_text(
        "What is the customer's name? (Type /cancel to abort)",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Name cannot be empty. Please enter the customer's name:")
        return NAME
    context.user_data['customer_name'] = text
    await update.message.reply_text("What is their phone number?")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    context.user_data['phone'] = phone
    await update.message.reply_text("What is the delivery address?")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Address cannot be empty. Please enter the address:")
        return ADDRESS
    context.user_data['address'] = text
    
    products = get_active_products()
    if not products:
        await update.message.reply_text("No active products available. Please ask an admin to add products.")
        return ConversationHandler.END
        
    keyboard = [[f"🟢 {p['product_name']}"] for p in products]
    
    await update.message.reply_text(
        "Choose Product:", 
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return PRODUCT

async def get_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_selection = update.message.text.replace("🟢 ", "").strip()
    product_details = get_product_by_name(product_selection)
    
    if not product_details:
        await update.message.reply_text("Please select a valid product from the menu below:")
        return PRODUCT
        
    context.user_data['product'] = product_details['product_name']
    context.user_data['unit_price'] = float(product_details['unit_price'])
    context.user_data['delivery_fee'] = float(product_details['delivery_fee'])
    
    await update.message.reply_text("What is the quantity?", reply_markup=ReplyKeyboardRemove())
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qty = int(update.message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Invalid quantity. Must be a number greater than 0. Try again:")
        return QUANTITY
        
    context.user_data['quantity'] = qty
    
    unit_price = context.user_data['unit_price']
    delivery = context.user_data['delivery_fee']
    subtotal = unit_price * qty
    total = subtotal + delivery
    
    context.user_data['total_price'] = total
    
    await update.message.reply_text("When will this order be sent out? (e.g., 'Tomorrow', 'ASAP', '2026-07-01')")
    return DISPATCH_DATE

async def get_dispatch_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Date cannot be empty. When will this order be sent out?")
        return DISPATCH_DATE
        
    context.user_data['dispatch_date'] = text
    
    unit_price = context.user_data['unit_price']
    delivery = context.user_data['delivery_fee']
    total = context.user_data['total_price']
    
    header = "ORDER PREVIEW".center(40)
    
    preview = (
        "========================================\n"
        f"{header}\n\n"
        f"Customer       : {context.user_data['customer_name']}\n"
        f"Phone Number   : {context.user_data['phone']}\n"
        f"Address        : {context.user_data['address']}\n\n"
        f"Product        : {context.user_data['product']}\n"
        f"Quantity       : {context.user_data['quantity']}\n"
        f"Unit Price     : ${unit_price:.2f}\n"
        f"Delivery Fee   : ${delivery:.2f}\n"
        f"TOTAL          : ${total:.2f}\n\n"
        f"Delivery Date  : {context.user_data['dispatch_date']}\n"
        "========================================"
    )
    
    reply_keyboard = [['✅ Confirm', '❌ Cancel']]
    
    # Wrapped in HTML <pre> tags to align the colons perfectly on mobile
    await update.message.reply_text(
        f"<pre>{preview}</pre>\nDoes this look correct?", 
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='HTML'
    )
    return CONFIRM
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text

    if answer == '✅ Confirm':
        order_number = save_order(
            context.user_data['customer_name'],
            context.user_data['phone'],
            context.user_data['address'],
            context.user_data['product'],
            context.user_data['quantity'],
            context.user_data['total_price'],
            context.user_data['dispatch_date'],
            context.user_data['staff_id'],
            context.user_data['staff_username'],
            context.user_data['staff_first_name']
        )
        context.user_data['order_number'] = order_number
        
        await send_order_to_group(context, context.user_data)
        
        await update.message.reply_text(
            f"✅ Order {order_number} saved and sent to the group!",
            reply_markup=ReplyKeyboardRemove()
        )
    elif answer == '❌ Cancel':
        await update.message.reply_text("❌ Order cancelled.", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Please choose '✅ Confirm' or '❌ Cancel'.")
        return CONFIRM
        
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("❌ Order cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

order_handler = ConversationHandler(
    entry_points=[CommandHandler('neworder', neworder)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
        PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product)],
        QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
        DISPATCH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dispatch_date)],
        CONFIRM: [MessageHandler(filters.Regex('^(✅ Confirm|❌ Cancel)$'), confirm_order)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)