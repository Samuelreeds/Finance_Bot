import os
import asyncio
import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Load Admin ID from .env
load_dotenv()
ADMIN_CHAT_ID = str(os.getenv("ADMIN_CHAT_ID"))

from utils.logger import logger

# Existing Services
from services.template_parser import parse_template, validate_finance
from services.product_service import get_active_products, get_product_by_id
from services.database_service import save_order, save_expense, save_income
from services.telegram_service import send_order_to_group, send_finance_to_group

# Report Services
from handlers.report import send_report_menu, generate_and_send_report

# Manage (CRUD) Services
from handlers.manage_handler import send_manage_menu, handle_search_input

def get_main_menu_keyboard(user_id: int | str) -> ReplyKeyboardMarkup:
    """Builds the menu based on user permissions."""
    keyboard = [
        [KeyboardButton("📦 New Order"), KeyboardButton("🎨 AI Poster")],
        [KeyboardButton("💸 Expense"), KeyboardButton("💰 Income")],
        [KeyboardButton("📊 Reports"), KeyboardButton("📂 Manage Records")]
    ]
    
    if str(user_id) == ADMIN_CHAT_ID:
        keyboard.append([KeyboardButton("📦 Inventory"), KeyboardButton("👥 Customers")])
        keyboard.append([KeyboardButton("⚙️ System Settings"), KeyboardButton("🪙 Token Manager")])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the persistent Main Menu keyboard dynamically based on permissions."""
    user_id = update.effective_user.id
    custom_keyboard = get_main_menu_keyboard(user_id)
    await update.message.reply_text("Welcome! Choose an action below:", reply_markup=custom_keyboard)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global listener for Menu buttons, Text Templates, and Photo Templates."""
    if update.message.chat.type != 'private':
        return

    # --- 0. CHECK FOR ACTIVE CRUD SEARCH ---
    if update.message.text and await handle_search_input(update, context):
        return

    # --- 1. MEDIA GROUP ACCUMULATION ---
    mg_id = update.message.media_group_id
    if mg_id and update.message.photo:
        if 'mg_files' not in context.user_data:
            context.user_data['mg_files'] = {}
        if mg_id not in context.user_data['mg_files']:
            context.user_data['mg_files'][mg_id] = []
        
        context.user_data['mg_files'][mg_id].append(update.message.photo[-1].file_id)

    # --- 2. HANDLE TEXT INPUT & BUTTONS ---
    text = update.message.text or update.message.caption
    
    if not text:
        if mg_id and 'mg_drafts' in context.user_data and mg_id in context.user_data['mg_drafts']:
            draft = context.user_data['mg_drafts'][mg_id]
            file_list = context.user_data['mg_files'][mg_id]
            
            draft['telegram_file_id'] = ",".join(file_list)
            
            count = len(file_list)
            title = "INCOME PREVIEW" if draft['type'] == 'income' else "EXPENSE PREVIEW"
            image_label = "Reference Images" if draft['type'] == 'income' else "Receipt Images"
            
            preview = (
                "==============================\n"
                f"{title.center(40)}\n"
                "==============================\n"
                f"Amount         : ${draft['amount']:.2f}\n"
                f"Description    : {draft['description']}\n"
                f"{image_label}: Yes ({count} attached)\n"
                "=============================="
            )
            keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data="confirm"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
            
            sent_msg = context.user_data['mg_messages'][mg_id]
            try:
                await sent_msg.edit_text(f"<pre>{preview}</pre>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            except Exception:
                pass 
        return

    user_id = str(update.effective_user.id)

    # --- GUARDRAIL FOR ADMIN BUTTON CLICKS ---
    admin_buttons = ["📦 Inventory", "👥 Customers", "⚙️ System Settings", "🪙 Token Manager"]
    if text in admin_buttons:
        if user_id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ Unauthorized access. Restricted to administrators.")
        else:
            await update.message.reply_text(f"🔧 '{text}' module is currently under construction.")
        return
    # -----------------------------------------

    # Menu Buttons
    if text == "📦 New Order":
        await update.message.reply_text(
            "📋 *Copy, fill out, and send this form:*\n\n"
            "Customer :\n"
            "Phone Number :\n"
            "Address :\n"
            "Quantity :\n"
            "Delivery Date :",
            parse_mode="Markdown"
        )
        return
        
    if text == "💸 Expense" or text == "💰 Income":
        context.user_data['active_finance_type'] = 'income' if 'Income' in text else 'expense'
        await update.message.reply_text(
            "Attach receipt/proof images if available.\n\n"
            "Amount :\n"
            "Description :"
        )
        return

    if text == "📊 Reports":
        await send_report_menu(update, context)
        return

    if text == "📂 Manage Records":
        await send_manage_menu(update, context)
        return

    # --- 3. PARSE TEMPLATE SUBMISSIONS ---
    parsed_data = parse_template(text)
    if not parsed_data:
        return 
        
    user = update.effective_user
    created_by = user.first_name or user.username or "Staff"

    # ROUTE: Order Template
    if 'customer' in parsed_data:
        required_fields = ['customer', 'phone number', 'address', 'quantity', 'delivery date']
        missing = [f.title() for f in required_fields if f not in parsed_data]
        
        if missing:
            await update.message.reply_text(f"❌ The following fields are missing:\n- " + "\n- ".join(missing) + "\n\nPlease correct the template and send it again.")
            return
            
        try:
            qty = int(parsed_data['quantity'])
        except ValueError:
            await update.message.reply_text("❌ Quantity must be a number.")
            return

        context.user_data['partial_order'] = {
            'customer_name': parsed_data['customer'],
            'phone': parsed_data['phone number'],
            'address': parsed_data['address'],
            'quantity': qty,
            'delivery_date': parsed_data['delivery date'],
            'created_by': created_by
        }
        
        products = get_active_products()
        if not products:
            await update.message.reply_text("❌ No active products found. Please ask an admin to add products.")
            return

        keyboard = []
        for p in products:
            keyboard.append([InlineKeyboardButton(p['product_name'], callback_data=f"selprod_{p['id']}")])
        
        await update.message.reply_text("📦 *Select the Product for this order:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # ROUTE: Finance Template (Expense/Income)
    if 'amount' in parsed_data and 'description' in parsed_data:
        finance_type = context.user_data.get('active_finance_type')
        if not finance_type:
            await update.message.reply_text("❌ Please select 'Expense' or 'Income' from the Main Menu first so I know where to file this.")
            return
            
        missing = validate_finance(parsed_data)
        if missing:
            await update.message.reply_text(f"❌ Missing fields:\n- " + "\n- ".join(missing))
            return
            
        try:
            amount = float(parsed_data['amount'].replace('$', ''))
        except ValueError:
            await update.message.reply_text("❌ Amount must be a number.")
            return
            
        file_id_list = []
        if mg_id:
            file_id_list = context.user_data.get('mg_files', {}).get(mg_id, [])
        elif update.message.photo:
            file_id_list.append(update.message.photo[-1].file_id)
        
        file_id_string = ",".join(file_id_list) if file_id_list else None
        has_image = f"Yes ({len(file_id_list)} attached)" if file_id_string else "No"
        
        context.user_data['draft'] = {
            'type': finance_type,
            'amount': amount,
            'description': parsed_data['description'],
            'telegram_file_id': file_id_string,
            'created_by': created_by
        }
        
        title = "INCOME PREVIEW" if finance_type == 'income' else "EXPENSE PREVIEW"
        image_label = "Reference Images" if finance_type == 'income' else "Receipt Images"
        
        preview = (
            "==============================\n"
            f"{title.center(40)}\n"
            "==============================\n"
            f"Amount         : ${amount:.2f}\n"
            f"Description    : {parsed_data['description']}\n"
            f"{image_label}: {has_image}\n"
            "=============================="
        )
        
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data="confirm"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
        sent_msg = await update.message.reply_text(f"<pre>{preview}</pre>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        
        if mg_id:
            if 'mg_drafts' not in context.user_data:
                context.user_data['mg_drafts'] = {}
            if 'mg_messages' not in context.user_data:
                context.user_data['mg_messages'] = {}
                
            context.user_data['mg_drafts'][mg_id] = context.user_data['draft']
            context.user_data['mg_messages'][mg_id] = sent_msg
            
        return

    # ROUTE: Custom Date Report
    if 'start date' in parsed_data and 'end date' in parsed_data:
        try:
            start_date = datetime.datetime.strptime(parsed_data['start date'], "%Y-%m-%d")
            end_date = datetime.datetime.strptime(parsed_data['end date'], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            await generate_and_send_report(update, context, start_date, end_date, "Custom Date Range")
        except ValueError:
            await update.message.reply_text("❌ Invalid date format. Please ensure dates are exactly YYYY-MM-DD.")
        return


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes Inline Keyboard Button Clicks."""
    query = update.callback_query
    data = query.data
    
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Failed to answer callback: {e}")
    
    # -----------------------------------------
    # PRODUCT SELECTION CALLBACK (NEW ORDER)
    # -----------------------------------------
    if data.startswith("selprod_"):
        product_id = int(data.split("_")[1])
        partial_order = context.user_data.get('partial_order')
        
        if not partial_order:
            await query.edit_message_text("❌ Session expired. Please submit the order form again.")
            return
            
        product = get_product_by_id(product_id)
        if not product:
            await query.edit_message_text("❌ Product not found in database.")
            return

        context.user_data['partial_order']['product_id'] = product['id']
        context.user_data['partial_order']['product_name'] = product['product_name']
        context.user_data['partial_order']['unit_price'] = float(product['unit_price'])

        keyboard = [
            [InlineKeyboardButton("📍 Phnom Penh ($2)", callback_data="delopt_Phnom Penh_2")],
            [InlineKeyboardButton("🗺 Provinces ($3)", callback_data="delopt_Province_3")],
            [InlineKeyboardButton("🏪 Pickup ($0)", callback_data="delopt_Pickup_0")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        await query.edit_message_text(
            f"📦 *Product Selected:* {product['product_name']}\n\n📍 *Choose Delivery Option:*", 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )
        return

    # -----------------------------------------
    # DELIVERY OPTION SELECTION (NEW ORDER)
    # -----------------------------------------
    if data.startswith("delopt_"):
        parts = data.split("_")
        method = parts[1]
        fee = float(parts[2])
        
        partial_order = context.user_data.get('partial_order')
        if not partial_order:
            await query.edit_message_text("❌ Session expired. Please submit the order form again.")
            return
            
        qty = partial_order['quantity']
        unit_price = partial_order['unit_price']
        subtotal = unit_price * qty
        total = subtotal + fee

        address = "PICKUP" if method == "Pickup" else partial_order['address']

        context.user_data['draft'] = {
            'type': 'order',
            'customer_name': partial_order['customer_name'],
            'phone': partial_order['phone'],
            'address': address,
            'product_id': partial_order['product_id'],
            'product_name': partial_order['product_name'],
            'quantity': qty,
            'unit_price': unit_price,
            'delivery_fee': fee,
            'delivery_method': method,
            'total_price': total,
            'delivery_date': partial_order['delivery_date'],
            'created_by': partial_order['created_by']
        }
        
        context.user_data.pop('partial_order', None)
        
        draft = context.user_data['draft']
        method_emoji = "📍 " if method == "Phnom Penh" else "🗺 " if method == "Province" else "🏪 " if method == "Pickup" else ""

        summary = (
            "━━━━━━━━━━━━━━\n"
            "Order Summary\n"
            "━━━━━━━━━━━━━━\n"
            f"Product:\n{draft['product_name']}\n\n"
            f"Quantity:\n{draft['quantity']}\n\n"
            f"Delivery:\n{method_emoji}{draft['delivery_method']}\n\n"
            f"Delivery Fee:\n${draft['delivery_fee']:.2f}\n\n"
            f"Total:\n${draft['total_price']:.2f}\n"
            "━━━━━━━━━━━━━━"
        )

        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data="confirm"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
        await query.edit_message_text(f"<pre>{summary}</pre>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return

    # -----------------------------------------
    # ORDER & FINANCE CALLBACKS
    # -----------------------------------------
    if data in ['confirm', 'cancel']:
        if data == 'cancel':
            context.user_data.pop('draft', None)
            context.user_data.pop('partial_order', None)
            await query.edit_message_text("❌ Action cancelled.")
            return
            
        if data == 'confirm':
            draft = context.user_data.get('draft')
            if not draft:
                await query.edit_message_text("❌ Error: Draft not found or expired.")
                return
            
            await query.edit_message_text("⏳ Processing transaction... Writing to database.")
            try:
                if draft['type'] == 'order':
                    order_num = save_order(
                        draft['customer_name'], draft['phone'], draft['address'], 
                        draft['product_id'], draft['quantity'], draft['unit_price'], 
                        draft['delivery_fee'], draft['total_price'], draft['delivery_date'], draft['created_by'],
                        delivery_method=draft.get('delivery_method', 'Phnom Penh')
                    )
                    draft['order_number'] = order_num
                    await send_order_to_group(context, draft)
                    await query.edit_message_text(f"✅ Order {order_num} saved and sent to group!")
                    
                elif draft['type'] == 'expense':
                    save_expense(draft['amount'], draft['description'], draft['telegram_file_id'], draft['created_by'])
                    await send_finance_to_group(context, draft, is_income=False)
                    await query.edit_message_text("✅ Expense saved and sent to group!")
                    
                elif draft['type'] == 'income':
                    save_income(draft['amount'], draft['description'], draft['telegram_file_id'], draft['created_by'])
                    await send_finance_to_group(context, draft, is_income=True)
                    await query.edit_message_text("✅ Income saved and sent to group!")
            except Exception as e:
                logger.error(f"Transaction failed: {e}", exc_info=True)
                await query.edit_message_text(f"❌ Database error occurred: {str(e)}")
            finally:
                context.user_data.pop('draft', None)