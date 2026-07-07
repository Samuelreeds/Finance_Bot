import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.logger import logger
from services import crud_service, update_service
from services.product_service import get_active_products, get_product_by_id
from services.telegram_service import send_order_to_group, send_finance_to_group

def get_order_edit_fields_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Customer Name", callback_data=f"edit_f_ord_{order_id}_customer_name"),
         InlineKeyboardButton("📱 Phone Number", callback_data=f"edit_f_ord_{order_id}_phone")],
        [InlineKeyboardButton("📍 Address", callback_data=f"edit_f_ord_{order_id}_address"),
         InlineKeyboardButton("📦 Product", callback_data=f"edit_f_ord_{order_id}_product")],
        [InlineKeyboardButton("🔢 Quantity", callback_data=f"edit_f_ord_{order_id}_quantity"),
         InlineKeyboardButton("📅 Delivery Date", callback_data=f"edit_f_ord_{order_id}_delivery_date")],
        [InlineKeyboardButton("🔄 Status", callback_data=f"edit_f_ord_{order_id}_status")],
        [InlineKeyboardButton("⬅ Back to Record", callback_data=f"edit_back_ord_{order_id}")]
    ])

def get_finance_edit_fields_keyboard(module: str, record_id: int) -> InlineKeyboardMarkup:
    img_lbl = "🖼 Reference Image" if module == "inc" else "🧾 Receipt Image"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 Amount", callback_data=f"edit_f_{module}_{record_id}_amount"),
         InlineKeyboardButton("📝 Description", callback_data=f"edit_f_{module}_{record_id}_description")],
        [InlineKeyboardButton(img_lbl, callback_data=f"edit_f_{module}_{record_id}_image")],
        [InlineKeyboardButton("⬅ Back to Record", callback_data=f"edit_back_{module}_{record_id}")]
    ])

def get_status_selection_keyboard(order_id: int) -> InlineKeyboardMarkup:
    statuses = ["Pending", "Processing", "Dispatched", "Delivered", "Cancelled"]
    kb = [[InlineKeyboardButton(st, callback_data=f"edit_st_{order_id}_{st}")] for st in statuses]
    kb.append([InlineKeyboardButton("⬅ Cancel", callback_data=f"edit_open_ord_{order_id}")])
    return InlineKeyboardMarkup(kb)

def get_product_selection_keyboard(order_id: int) -> InlineKeyboardMarkup:
    products = get_active_products()
    kb = [[InlineKeyboardButton(p['product_name'], callback_data=f"edit_pr_{order_id}_{p['id']}")] for p in products]
    kb.append([InlineKeyboardButton("⬅ Cancel", callback_data=f"edit_open_ord_{order_id}")])
    return InlineKeyboardMarkup(kb)

def build_diff_preview_message(module: str, old_data: dict, new_data: dict) -> str:
    lines = ["━━━━━━━━━━━━━━━━━━", f"<b>{module.upper()} UPDATE PREVIEW</b>", "━━━━━━━━━━━━━━━━━━"]
    changes_found = False
    for key in new_data:
        old_val = str(old_data.get(key, ''))
        new_val = str(new_data.get(key, ''))
        if old_val != new_val:
            changes_found = True
            lbl = key.replace('_', ' ').title()
            lines.append(f"<b>{lbl}</b>\n{old_val} ➡ <b>{new_val}</b>\n")
    if not changes_found:
        return "⚠️ No changes detected. Everything matches the existing database record."
    lines.append("━━━━━━━━━━━━━━━━━━\n<i>Please confirm your changes below:</i>")
    return "\n".join(lines)

async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try: await query.answer()
    except Exception as e: logger.error(f"Failed to answer edit callback: {e}")
    data = query.data
    logger.info(f"Edit callback triggered: {data}")
    user = update.effective_user
    updated_by = user.first_name or user.username or "Staff"

    if data.startswith("edit_back_"):
        parts = data.split("_")
        module, rec_id = parts[2], int(parts[3])
        context.user_data.pop('edit_session', None)
        cmd_map = {"ord": f"/view_order_{rec_id}", "exp": f"/view_exp_{rec_id}", "inc": f"/view_inc_{rec_id}"}
        await query.message.reply_text(f"<i>Returned to details. Click {cmd_map[module]} to view.</i>", parse_mode="HTML")
        await query.message.delete()
        return

    if data.startswith("edit_open_"):
        parts = data.split("_")
        module, rec_id = parts[2], int(parts[3])
        if module == "ord":
            old_data = crud_service.get_order_by_id(rec_id)
            kb = get_order_edit_fields_keyboard(rec_id)
            title = f"Order #{old_data.get('order_number', rec_id)}"
        elif module == "exp":
            old_data = crud_service.get_expense_by_id(rec_id)
            kb = get_finance_edit_fields_keyboard("exp", rec_id)
            title = f"Expense #{rec_id}"
        elif module == "inc":
            old_data = crud_service.get_income_by_id(rec_id)
            kb = get_finance_edit_fields_keyboard("inc", rec_id)
            title = f"Income #{rec_id}"
        context.user_data['edit_session'] = {'module': module, 'record_id': rec_id, 'old_data': dict(old_data), 'new_data': dict(old_data)}
        await query.edit_message_text(f"✏ <b>Editing {title}</b>\n\nSelect a field below to modify:", reply_markup=kb, parse_mode="HTML")
        return

    if data.startswith("edit_f_"):
        parts = data.split("_")
        module, rec_id, field = parts[2], int(parts[3]), "_".join(parts[4:])
        logger.info(f"Field selected for edit: {field} on {module} #{rec_id}")
        if field == "status":
            await query.edit_message_text("🔄 Select new Status:", reply_markup=get_status_selection_keyboard(rec_id)); return
        if field == "product":
            await query.edit_message_text("📦 Select new Product:", reply_markup=get_product_selection_keyboard(rec_id)); return
        context.user_data['edit_awaiting_input'] = {'module': module, 'record_id': rec_id, 'field': field}
        lbl = field.replace('_', ' ').title()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Cancel", callback_data=f"edit_open_{module}_{rec_id}")]])
        await query.edit_message_text(f"✏ Enter new value for <b>{lbl}</b>:", reply_markup=kb, parse_mode="HTML")
        return

    if data.startswith("edit_st_"):
        parts = data.split("_")
        rec_id, new_status = int(parts[2]), parts[3]
        session = context.user_data.get('edit_session')
        if not session: await query.edit_message_text("❌ Edit session expired."); return
        session['new_data']['status'] = new_status
        await show_edit_preview(query, context); return

    if data.startswith("edit_pr_"):
        parts = data.split("_")
        rec_id, prod_id = int(parts[2]), int(parts[3])
        session = context.user_data.get('edit_session')
        if not session: await query.edit_message_text("❌ Edit session expired."); return
        product = get_product_by_id(prod_id)
        qty = int(session['new_data']['quantity'])
        unit_price = float(product['unit_price'])
        delivery = float(product['delivery_fee'])
        session['new_data'].update({'product_id': product['id'], 'product_name': product['product_name'], 'unit_price': unit_price, 'delivery_fee': delivery, 'total_price': (unit_price * qty) + delivery})
        await show_edit_preview(query, context); return

    if data in ["edit_confirm", "edit_cancel"]:
        session = context.user_data.get('edit_session')
        if not session: await query.edit_message_text("❌ Session expired."); return
        if data == "edit_cancel":
            context.user_data.pop('edit_session', None)
            await query.edit_message_text("❌ Modification cancelled."); return
        module = session['module']
        rec_id = session['record_id']
        old_d = session['old_data']
        new_d = session['new_data']
        await query.edit_message_text("⏳ Writing modifications to database...")
        try:
            if module == "ord":
                update_service.update_order(rec_id, old_d, new_d, updated_by)
                await send_order_to_group(context, new_d, is_update=True, changed_by=updated_by)
            elif module == "exp":
                update_service.update_expense(rec_id, old_d, new_d, updated_by)
                await send_finance_to_group(context, new_d, is_income=False, is_update=True, changed_by=updated_by)
            elif module == "inc":
                update_service.update_income(rec_id, old_d, new_d, updated_by)
                await send_finance_to_group(context, new_d, is_income=True, is_update=True, changed_by=updated_by)
            await query.edit_message_text(f"✅ Record #{rec_id} successfully updated and group notified!")
        except Exception as e:
            logger.error(f"Update transaction failed: {e}", exc_info=True)
            await query.edit_message_text("❌ Database update failed. The transaction was rolled back.")
        finally:
            context.user_data.pop('edit_session', None)
        return

async def show_edit_preview(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = context.user_data.get('edit_session')
    mod = session['module']
    msg = build_diff_preview_message(mod, session['old_data'], session['new_data'])
    if "No changes detected" in msg:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back to Menu", callback_data=f"edit_open_{mod}_{session['record_id']}")]])
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data="edit_confirm"), InlineKeyboardButton("❌ Cancel", callback_data="edit_cancel")],
            [InlineKeyboardButton("⬅ Keep Editing", callback_data=f"edit_open_{mod}_{session['record_id']}")]
        ])
    await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    pending = context.user_data.get('edit_awaiting_input')
    if not pending: return False
    session = context.user_data.get('edit_session')
    if not session:
        context.user_data.pop('edit_awaiting_input', None); return False
    field = pending['field']
    mod = pending['module']
    rec_id = pending['record_id']

    if field == "image":
        if not update.message.photo:
            await update.message.reply_text("❌ Please upload a valid image."); return True
        file_ids = [photo.file_id for photo in update.message.photo]
        session['new_data']['telegram_file_id'] = ",".join(file_ids)
        context.user_data.pop('edit_awaiting_input', None)
        msg = build_diff_preview_message(mod, session['old_data'], session['new_data'])
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data="edit_confirm"), InlineKeyboardButton("❌ Cancel", callback_data="edit_cancel")]])
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
        return True

    text = update.message.text.strip() if update.message.text else ""
    if not text: return True
    logger.info(f"Input received for edit field {field}: '{text}'")

    if field == "phone" and not text.isdigit():
        await update.message.reply_text("❌ Phone number must contain only numerical digits."); return True
    if field == "amount":
        try:
            val = float(text.replace('$', ''))
            if val < 0: raise ValueError
            session['new_data']['amount'] = val
        except ValueError:
            await update.message.reply_text("❌ Amount must be a positive decimal number."); return True
    elif field == "quantity":
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
            session['new_data']['quantity'] = qty
            up = float(session['new_data']['unit_price'])
            df = float(session['new_data']['delivery_fee'])
            session['new_data']['total_price'] = (up * qty) + df
        except ValueError:
            await update.message.reply_text("❌ Quantity must be a positive integer."); return True
    elif field == "delivery_date":
        if len(text) < 3:
            await update.message.reply_text("❌ Delivery Date cannot be empty or too short."); return True
        session['new_data']['delivery_date'] = text
    else:
        session['new_data'][field] = text

    context.user_data.pop('edit_awaiting_input', None)
    msg = build_diff_preview_message(mod, session['old_data'], session['new_data'])
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data="edit_confirm"), InlineKeyboardButton("❌ Cancel", callback_data="edit_cancel")],
        [InlineKeyboardButton("⬅ Keep Editing", callback_data=f"edit_open_{mod}_{rec_id}")]
    ])
    await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
    return True