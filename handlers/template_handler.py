import os
import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Load Admin ID from .env
load_dotenv()
ADMIN_CHAT_ID = str(os.getenv("ADMIN_CHAT_ID"))

# Existing Services
from services.template_parser import parse_template, validate_finance
from services.product_service import get_active_products, get_product_by_id
from services.database_service import save_order, save_expense, save_income
from services.telegram_service import format_order_message, send_order_to_group, send_finance_to_group

# Report Services
from handlers.report import send_report_menu, generate_and_send_report

# AI Poster Services
from services.token_service import get_balance, get_poster_price, deduct_tokens, add_tokens
from services.prompt_service import get_active_prompts, get_prompt_by_id
from services.ai_service import generate_poster, save_poster_history


def get_main_menu_keyboard(user_id: int | str) -> ReplyKeyboardMarkup:
    """Builds the menu based on user permissions."""
    # 1. Standard buttons visible to everyone
    keyboard = [
        [KeyboardButton("📦 New Order"), KeyboardButton("🎨 AI Poster")],
        [KeyboardButton("💸 Expense"), KeyboardButton("💰 Income")],
        [KeyboardButton("📊 Reports")]
    ]
    
    # 2. Admin buttons appended ONLY if your ID matches
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

    # --- 1. HANDLE PHOTO UPLOADS (AI POSTER) ---
    if update.message.photo:
        if context.user_data.get('awaiting_poster_image'):
            # Get the highest resolution photo
            file_id = update.message.photo[-1].file_id
            context.user_data['poster_file_id'] = file_id
            context.user_data['awaiting_poster_image'] = False
            
            prompts = get_active_prompts()
            if not prompts:
                await update.message.reply_text("No active poster styles available. Please contact an admin.")
                return
                
            # Create a button for each active prompt
            keyboard = [[InlineKeyboardButton(p['name'], callback_data=f"pstyle_{p['id']}")] for p in prompts]
            await update.message.reply_text("Select a Poster Style:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

    # --- 2. HANDLE TEXT INPUT & BUTTONS ---
    text = update.message.text or update.message.caption
    if not text:
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
            "Attach a receipt/proof image if available.\n\n"
            "Amount :\n"
            "Description :"
        )
        return

    if text == "📊 Reports":
        await send_report_menu(update, context)
        return

    if text == "🎨 AI Poster":
        balance = get_balance(user_id)
        price = get_poster_price()
        
        if balance < price:
            await update.message.reply_text(f"You don't have enough tokens (Need {price}, Have {balance}).\nPlease contact the administrator to purchase more.")
            return
            
        context.user_data['awaiting_poster_image'] = True
        await update.message.reply_text("Please upload ONE food image.")
        return

    # --- 3. PARSE TEMPLATE SUBMISSIONS ---
    parsed_data = parse_template(text)
    if not parsed_data:
        return # Not a template, ignore normal chat
        
    user = update.effective_user
    created_by = user.first_name or user.username or "Staff"

    # ROUTE: Order Template
    if 'customer' in parsed_data:
        # Check required fields (Product is omitted here, we will ask via buttons next)
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

        # Temporarily save the customer info
        context.user_data['partial_order'] = {
            'customer_name': parsed_data['customer'],
            'phone': parsed_data['phone number'],
            'address': parsed_data['address'],
            'quantity': qty,
            'delivery_date': parsed_data['delivery date'],
            'created_by': created_by
        }
        
        # Fetch active products from database to generate buttons
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
            
        file_id = update.message.photo[-1].file_id if update.message.photo else None
        has_image = "Yes" if file_id else "No"
        
        context.user_data['draft'] = {
            'type': finance_type,
            'amount': amount,
            'description': parsed_data['description'],
            'telegram_file_id': file_id,
            'created_by': created_by
        }
        
        title = "INCOME PREVIEW" if finance_type == 'income' else "EXPENSE PREVIEW"
        image_label = "Reference Image" if finance_type == 'income' else "Receipt Image"
        
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
        await update.message.reply_text(f"<pre>{preview}</pre>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
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
    user_id = str(update.effective_user.id)
    
    # -----------------------------------------
    # PRODUCT SELECTION CALLBACK (NEW ORDER)
    # -----------------------------------------
    if data.startswith("selprod_"):
        await query.answer()
        product_id = int(data.split("_")[1])
        partial_order = context.user_data.get('partial_order')
        
        if not partial_order:
            await query.edit_message_text("❌ Session expired. Please submit the order form again.")
            return
            
        product = get_product_by_id(product_id)
        if not product:
            await query.edit_message_text("❌ Product not found in database.")
            return
            
        qty = partial_order['quantity']
        unit_price = float(product['unit_price'])
        delivery = float(product['delivery_fee'])
        subtotal = unit_price * qty
        total = subtotal + delivery

        # Complete the draft object now that we have the product
        context.user_data['draft'] = {
            'type': 'order',
            'customer_name': partial_order['customer_name'],
            'phone': partial_order['phone'],
            'address': partial_order['address'],
            'product_id': product['id'],
            'product_name': product['product_name'],
            'quantity': qty,
            'unit_price': unit_price,
            'delivery_fee': delivery,
            'total_price': total,
            'delivery_date': partial_order['delivery_date'],
            'created_by': partial_order['created_by']
        }
        
        # Clean up the partial draft
        context.user_data.pop('partial_order', None)
        
        preview = format_order_message(context.user_data['draft'])
        keyboard = [[InlineKeyboardButton("✅ Confirm", callback_data="confirm"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
        
        await query.edit_message_text(f"<pre>{preview}</pre>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return

    # -----------------------------------------
    # AI POSTER CALLBACKS
    # -----------------------------------------
    if data.startswith("pstyle_"):
        await query.answer()
        prompt_id = int(data.split("_")[1])
        prompt_data = get_prompt_by_id(prompt_id)
        price = get_poster_price()
        balance = get_balance(user_id)
        
        context.user_data['poster_draft'] = {
            'prompt_id': prompt_id,
            'price': price
        }
        
        msg = (
            f"Selected Style\n{prompt_data['name']}\n\n"
            f"Token Cost\n{price} Tokens\n\n"
            f"Current Balance\n{balance} Tokens"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Generate", callback_data="poster_generate"), 
             InlineKeyboardButton("❌ Cancel", callback_data="poster_cancel")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "poster_cancel":
        await query.answer()
        context.user_data.pop('poster_draft', None)
        context.user_data.pop('poster_file_id', None)
        await query.edit_message_text("❌ Poster generation cancelled.")
        return

    if data == "poster_generate":
        await query.answer()
        draft = context.user_data.get('poster_draft')
        file_id = context.user_data.get('poster_file_id')
        
        if not draft or not file_id:
            await query.edit_message_text("❌ Session expired. Please start again.")
            return
            
        prompt_data = get_prompt_by_id(draft['prompt_id'])
        price = draft['price']
        
        # Deduct tokens transactionally
        if not deduct_tokens(user_id, price):
            await query.edit_message_text("❌ Insufficient tokens.")
            return
            
        await query.edit_message_text("⏳ Generating poster... Please wait.")
        
        try:
            # Send to AI Pipeline (Now returns image bytes)
            generated_image_bytes = await generate_poster(context.bot, file_id, prompt_data['prompt'])
            
            # Deliver the actual image!
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, 
                photo=generated_image_bytes,
                caption="✅ Your AI Poster is Ready!"
            )
            
            # Save history (Saving a placeholder string since it's raw bytes, not a URL)
            save_poster_history(user_id, draft['prompt_id'], file_id, "Generated via Imagen 3", price, "SUCCESS")
            
        except Exception as e:
            print(f"\n--- AI PIPELINE ERROR --- \n{e}\n-------------------------\n")
            # Refund on failure
            add_tokens(user_id, price)
            save_poster_history(user_id, draft['prompt_id'], file_id, "ERROR", 0, "FAILED")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Poster generation failed.\nNo tokens were deducted.\nPlease try again.")
        # Clean up context
        context.user_data.pop('poster_draft', None)
        context.user_data.pop('poster_file_id', None)
        return

    # -----------------------------------------
    # ORDER & FINANCE CALLBACKS
    # -----------------------------------------
    if data in ['confirm', 'cancel']:
        await query.answer()
        
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
                
            if draft['type'] == 'order':
                order_num = save_order(
                    draft['customer_name'], draft['phone'], draft['address'], 
                    draft['product_id'], draft['quantity'], draft['unit_price'], 
                    draft['delivery_fee'], draft['total_price'], draft['delivery_date'], draft['created_by']
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
                
            context.user_data.pop('draft', None)