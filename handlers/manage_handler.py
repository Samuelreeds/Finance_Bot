import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ContextTypes
from utils.logger import logger
from services import crud_service, search_service

# --- UI BUILDERS ---

def get_module_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Orders", callback_data="manage_mod_orders")],
        [InlineKeyboardButton("💸 Expenses", callback_data="manage_mod_expenses")],
        [InlineKeyboardButton("💰 Income", callback_data="manage_mod_income")],
        [InlineKeyboardButton("⬅ Back", callback_data="manage_close")]
    ])

def get_action_keyboard(module: str) -> InlineKeyboardMarkup:
    titles = {"orders": "Orders", "expenses": "Expenses", "income": "Income"}
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📋 Today's {titles[module]}", callback_data=f"manage_act_{module}_today_0")],
        [InlineKeyboardButton("🔍 Search", callback_data=f"manage_act_{module}_search")],
        [InlineKeyboardButton("⬅ Back", callback_data="manage_root")]
    ])

def build_pagination_keyboard(module: str, action: str, current_page: int, total_records: int, limit: int = 10) -> InlineKeyboardMarkup:
    keyboard = []
    nav_row = []
    if current_page > 0:
        nav_row.append(InlineKeyboardButton("⬅ Prev", callback_data=f"manage_act_{module}_{action}_{current_page - 1}"))
    if (current_page + 1) * limit < total_records:
        nav_row.append(InlineKeyboardButton("Next ➡", callback_data=f"manage_act_{module}_{action}_{current_page + 1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data=f"manage_mod_{module}")])
    return InlineKeyboardMarkup(keyboard)

def format_record_list(records: list, module: str, current_page: int, total_records: int, limit: int = 10) -> str:
    if not records:
        return "━━━━━━━━━━━━━━━━━━━━\nNo records found.\n━━━━━━━━━━━━━━━━━━━━"
    lines = [f"━━━━━━━━━━━━━━━━━━━━\n<b>{module.upper()} RECORDS</b> (Page {current_page + 1}/{-(-total_records // limit)})\n━━━━━━━━━━━━━━━━━━━━"]
    for r in records:
        if module == "orders":
            dt_str = r['created_at'].strftime('%Y-%m-%d') if isinstance(r['created_at'], datetime.datetime) else str(r['created_at'])[:10]
            lines.append(f"<b>{r.get('order_number', 'N/A')}</b> | {r['customer_name']}\n{r.get('product_name', 'Product')} | ${float(r['total_price']):.2f} | {dt_str}\nID: <code>{r['id']}</code> | /view_order_{r['id']}\n━━━━━━━━━━━━━━━━━━━━")
        elif module == "expenses":
            dt_str = r['created_at'].strftime('%Y-%m-%d %H:%M') if isinstance(r['created_at'], datetime.datetime) else str(r['created_at'])[:16]
            lines.append(f"<b>${float(r['amount']):.2f}</b> | {r['description']}\nBy: {r['created_by']} | {dt_str}\nID: <code>{r['id']}</code> | /view_exp_{r['id']}\n━━━━━━━━━━━━━━━━━━━━")
        elif module == "income":
            dt_str = r['created_at'].strftime('%Y-%m-%d %H:%M') if isinstance(r['created_at'], datetime.datetime) else str(r['created_at'])[:16]
            lines.append(f"<b>${float(r['amount']):.2f}</b> | {r['description']}\nBy: {r['created_by']} | {dt_str}\nID: <code>{r['id']}</code> | /view_inc_{r['id']}\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("<i>Click a /view command above to see details.</i>")
    return "\n".join(lines)

# --- ENTRY POINT & CALLBACK ROUTER ---

async def send_manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Opening Manage Records root menu.")
    await update.message.reply_text("━━━━━━━━━━━━━━━━━━━━\n<b>Select Module</b>\n━━━━━━━━━━━━━━━━━━━━", reply_markup=get_module_selection_keyboard(), parse_mode="HTML")

async def handle_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try: await query.answer()
    except Exception as e: logger.error(f"Failed to answer callback query: {e}")
    data = query.data
    logger.info(f"Manage callback triggered: {data}")

    if data == "manage_close":
        await query.message.delete(); return
    if data == "manage_root":
        await query.edit_message_text("━━━━━━━━━━━━━━━━━━━━\n<b>Select Module</b>\n━━━━━━━━━━━━━━━━━━━━", reply_markup=get_module_selection_keyboard(), parse_mode="HTML"); return
    if data.startswith("manage_mod_"):
        module = data.split("_")[2]
        titles = {"orders": "Orders", "expenses": "Expenses", "income": "Income"}
        await query.edit_message_text(f"━━━━━━━━━━━━━━━━━━━━\n<b>{titles[module]}</b>\n━━━━━━━━━━━━━━━━━━━━", reply_markup=get_action_keyboard(module), parse_mode="HTML"); return
    if data.startswith("manage_act_"):
        parts = data.split("_")
        module, action = parts[2], parts[3]
        if action == "search":
            context.user_data['awaiting_search_module'] = module
            await query.edit_message_text(f"🔍 <b>Search {module.upper()}</b>\n\nPlease enter your search term below (Partial matching enabled):", parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Cancel", callback_data=f"manage_mod_{module}")]]))
            return
        page, limit = int(parts[4]), 10
        records, total = [], 0
        if action == "today":
            if module == "orders": records, total = crud_service.get_today_orders(page, limit)
            elif module == "expenses": records, total = crud_service.get_today_expenses(page, limit)
            elif module == "income": records, total = crud_service.get_today_income(page, limit)
        elif action == "sres":
            query_str = context.user_data.get('active_search_query', '')
            if module == "orders": records, total = search_service.search_orders(query_str, page, limit)
            elif module == "expenses": records, total = search_service.search_expenses(query_str, page, limit)
            elif module == "income": records, total = search_service.search_income(query_str, page, limit)
        await query.edit_message_text(format_record_list(records, module, page, total, limit), reply_markup=build_pagination_keyboard(module, action, page, total, limit), parse_mode="HTML")
        return

# --- SEARCH TEXT INPUT HANDLER ---

async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    module = context.user_data.get('awaiting_search_module')
    if not module: return False
    query_str = update.message.text.strip()
    logger.info(f"Processing search input for {module}: '{query_str}'")
    context.user_data['active_search_query'] = query_str
    context.user_data.pop('awaiting_search_module', None)
    page, limit = 0, 10
    if module == "orders": records, total = search_service.search_orders(query_str, page, limit)
    elif module == "expenses": records, total = search_service.search_expenses(query_str, page, limit)
    elif module == "income": records, total = search_service.search_income(query_str, page, limit)
    await update.message.reply_text(format_record_list(records, module, page, total, limit), reply_markup=build_pagination_keyboard(module, "sres", page, total, limit), parse_mode="HTML")
    return True

# --- VIEW DETAILS HANDLERS ---

async def view_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        order_id = int(update.message.text.split("_")[2])
        logger.info(f"Viewing details for Order ID: {order_id}")
        r = crud_service.get_order_by_id(order_id)
        if not r: await update.message.reply_text("❌ Order not found."); return
        dt_str = r['created_at'].strftime('%Y-%m-%d %I:%M %p') if isinstance(r['created_at'], datetime.datetime) else str(r['created_at'])
        msg = (
            "━━━━━━━━━━━━━━━━━━━━\n<b>ORDER DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Order No:</b> {r.get('order_number', 'N/A')}\n<b>Customer:</b> {r['customer_name']}\n"
            f"<b>Phone:</b> {r['phone']}\n<b>Address:</b> {r['address']}\n"
            f"<b>Product:</b> {r.get('product_name', 'N/A')}\n<b>Quantity:</b> {r['quantity']}\n"
            f"<b>Unit Price:</b> ${float(r['unit_price']):.2f}\n<b>Delivery Fee:</b> ${float(r['delivery_fee']):.2f}\n"
            f"<b>Total:</b> ${float(r['total_price']):.2f}\n<b>Delivery Date:</b> {r['delivery_date']}\n"
            f"<b>Status:</b> {r.get('status', 'Pending')}\n<b>Created By:</b> {r['created_by']}\n"
            f"<b>Created At:</b> {dt_str}\n━━━━━━━━━━━━━━━━━━━━"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏ Edit Order", callback_data=f"edit_open_ord_{order_id}")],
            [InlineKeyboardButton("⬅ Back", callback_data="manage_mod_orders")]
        ])
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error viewing order: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to load order details.")

async def view_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        exp_id = int(update.message.text.split("_")[2])
        logger.info(f"Viewing details for Expense ID: {exp_id}")
        r = crud_service.get_expense_by_id(exp_id)
        if not r: await update.message.reply_text("❌ Expense not found."); return
        dt_str = r['created_at'].strftime('%Y-%m-%d %I:%M %p') if isinstance(r['created_at'], datetime.datetime) else str(r['created_at'])
        msg = (
            "━━━━━━━━━━━━━━━━━━━━\n<b>EXPENSE DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Amount:</b> ${float(r['amount']):.2f}\n<b>Description:</b> {r['description']}\n"
            f"<b>Created By:</b> {r['created_by']}\n<b>Created At:</b> {dt_str}\n━━━━━━━━━━━━━━━━━━━━"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏ Edit Expense", callback_data=f"edit_open_exp_{exp_id}")],
            [InlineKeyboardButton("⬅ Back", callback_data="manage_mod_expenses")]
        ])
        file_id_string = r.get('telegram_file_id')
        if file_id_string:
            file_ids = [fid.strip() for fid in file_id_string.split(",") if fid.strip()]
            if len(file_ids) == 1:
                await update.message.reply_photo(photo=file_ids[0], caption=msg, parse_mode="HTML", reply_markup=kb)
            else:
                media_group = [InputMediaPhoto(media=fid, caption=msg if idx == 0 else None, parse_mode="HTML") for idx, fid in enumerate(file_ids)]
                await update.message.reply_media_group(media=media_group)
                await update.message.reply_text("<i>Use the button below to edit or navigate back:</i>", parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error viewing expense: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to load expense details.")

async def view_income_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        inc_id = int(update.message.text.split("_")[2])
        logger.info(f"Viewing details for Income ID: {inc_id}")
        r = crud_service.get_income_by_id(inc_id)
        if not r: await update.message.reply_text("❌ Income not found."); return
        dt_str = r['created_at'].strftime('%Y-%m-%d %I:%M %p') if isinstance(r['created_at'], datetime.datetime) else str(r['created_at'])
        msg = (
            "━━━━━━━━━━━━━━━━━━━━\n<b>INCOME DETAILS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Amount:</b> ${float(r['amount']):.2f}\n<b>Description:</b> {r['description']}\n"
            f"<b>Created By:</b> {r['created_by']}\n<b>Created At:</b> {dt_str}\n━━━━━━━━━━━━━━━━━━━━"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏ Edit Income", callback_data=f"edit_open_inc_{inc_id}")],
            [InlineKeyboardButton("⬅ Back", callback_data="manage_mod_income")]
        ])
        file_id_string = r.get('telegram_file_id')
        if file_id_string:
            file_ids = [fid.strip() for fid in file_id_string.split(",") if fid.strip()]
            if len(file_ids) == 1:
                await update.message.reply_photo(photo=file_ids[0], caption=msg, parse_mode="HTML", reply_markup=kb)
            else:
                media_group = [InputMediaPhoto(media=fid, caption=msg if idx == 0 else None, parse_mode="HTML") for idx, fid in enumerate(file_ids)]
                await update.message.reply_media_group(media=media_group)
                await update.message.reply_text("<i>Use the button below to edit or navigate back:</i>", parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error viewing income: {e}", exc_info=True)
        await update.message.reply_text("❌ Failed to load income details.")