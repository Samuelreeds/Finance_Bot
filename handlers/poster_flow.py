import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters,
    CommandHandler
)
from services.prompt_builder import parse_form_data, build_prompt
from services.template_service import get_food_templates, get_template_by_id
from services.ai_service import analyze_food_image, generate_poster_image, save_poster_history
from services.token_service import deduct_tokens, add_tokens, get_balance, get_poster_price

logger = logging.getLogger(__name__)

# States
UPLOADING_PHOTO, SELECTING_TEMPLATE, WAITING_FOR_FORM = range(3)

# Unified Information Form
FORM_TEMPLATE = """📋 **Copy, fill out, and send this form back:**

Food Name:
Price:
Promotion:
Call To Action:
Restaurant Name:
Phone Number:
Facebook Page:"""

async def start_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the Template-Based AI Poster Generator."""
    user_id = str(update.effective_user.id)
    balance = get_balance(user_id)
    price = get_poster_price()
    
    if balance < price:
        await update.message.reply_text(
            f"❌ You don't have enough tokens (Need {price}, Have {balance}).\n"
            "Please contact the administrator to purchase more."
        )
        return ConversationHandler.END

    context.user_data['poster_state'] = {}
    await update.message.reply_text("📸 Please upload the Food Image you want to use for the poster.")
    return UPLOADING_PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the photo and presents dynamic template options from the database."""
    file_id = update.message.photo[-1].file_id
    context.user_data['poster_state']['photo_id'] = file_id
    
    templates = get_food_templates()
    if not templates:
        await update.message.reply_text("❌ No poster templates are currently available in the database. Contact admin.")
        return ConversationHandler.END
        
    await update.message.reply_text("🔍 Fetching professional templates...")
    
    for t in templates:
        caption = f"🎨 **{t['template_name']}**\n{t['description']}"
        keyboard = [[InlineKeyboardButton("✅ Select This Template", callback_data=f"tpl_{t['id']}")]]
        
        # Display the template preview image alongside its selection button
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=t['preview_image'],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        
    return SELECTING_TEMPLATE

async def handle_template_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves chosen template and asks the user to fill the business form."""
    query = update.callback_query
    await query.answer()
    
    template_id = int(query.data.split('_')[1])
    context.user_data['poster_state']['template_id'] = template_id
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"✅ Great choice!\n\n{FORM_TEMPLATE}", 
        parse_mode="Markdown"
    )
    return WAITING_FOR_FORM

async def handle_form_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses form, injects data into the chosen template, and generates."""
    state = context.user_data.get('poster_state')
    if not state:
        await update.message.reply_text("❌ Session expired. Please restart by clicking 🎨 AI Poster.")
        return ConversationHandler.END
        
    text_input = update.message.text
    parsed_details = parse_form_data(text_input)
    
    # Require at least the Food Name and Price to be filled for decent results
    if not parsed_details.get("food_name") or not parsed_details.get("price"):
        await update.message.reply_text(
            "❌ Please ensure you fill out at least the `Food Name` and `Price`.\n"
            "Copy the form and try again.",
            parse_mode="Markdown"
        )
        return WAITING_FOR_FORM 
        
    state['form_data'] = parsed_details
    return await finalize_generation(update, context)

async def cancel_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the generation cleanly."""
    context.user_data.pop('poster_state', None)
    msg = "❌ Poster generation session closed."
    if update.callback_query:
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)
    return ConversationHandler.END

async def finalize_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Analyzes food, builds prompt via template, and renders image."""
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    state = context.user_data['poster_state']
    price = get_poster_price()
    
    status_msg = await context.bot.send_message(chat_id=chat_id, text="⏳ Analyzing food and generating your poster... Please wait.")
    
    if not deduct_tokens(user_id, price):
        await status_msg.edit_text("❌ Insufficient token balance available for execution.")
        return ConversationHandler.END

    try:
        # Download user image
        file = await context.bot.get_file(state['photo_id'])
        img_buffer = io.BytesIO()
        await file.download_to_memory(img_buffer)
        image_bytes = img_buffer.getvalue()

        # Step 1: AI describes the food accurately so Imagen 4 preserves it
        food_desc = await analyze_food_image(image_bytes)
        
        # Step 2: Inject the extracted description AND the user's form into the DB template
        state['form_data']['food_description'] = food_desc
        template_record = get_template_by_id(state['template_id'])
        
        final_prompt = build_prompt(template_record['prompt_template'], state['form_data'])
        
        # Step 3: Render via Imagen
        final_render = await generate_poster_image(final_prompt)
        
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=final_render,
            caption="✅ Your Professional Poster is Ready!"
        )
        save_poster_history(user_id, state['template_id'], state['photo_id'], "SUCCESS", price, "SUCCESS")
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Render runtime tracking fault: {e}")
        add_tokens(user_id, price) 
        save_poster_history(user_id, state['template_id'], state['photo_id'], "ERROR", 0, "FAILED")
        await context.bot.send_message(chat_id=chat_id, text="❌ Production pipeline failure encountered. Tokens have been refunded.")
        
    context.user_data.pop('poster_state', None)
    return ConversationHandler.END

poster_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^🎨 AI Poster$'), start_poster)],
    states={
        UPLOADING_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        SELECTING_TEMPLATE: [CallbackQueryHandler(handle_template_selection, pattern="^tpl_")],
        WAITING_FOR_FORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_form_submission)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_poster),
        MessageHandler(filters.Regex('^❌ Cancel$'), cancel_poster)
    ],
    per_message=False
)