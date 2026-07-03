# handlers/poster_flow.py
import logging
import re
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
from services.prompt_builder import build_poster_prompt
from services.ai_service import analyze_and_prompt, generate_poster_image, save_poster_history
from services.token_service import deduct_tokens, add_tokens, get_balance, get_poster_price

logger = logging.getLogger(__name__)

# States (Reduced from 3 to 2!)
UPLOADING_PHOTO, SELECTING_TEMPLATE, WAITING_FOR_FORM = range(3)

# The template form that users will copy and fill out
FORM_TEMPLATE = """📋 **Copy, fill out, and send this form back:**

Food Name : 
Current Price : 
Theme Color : 

--- Optional Fields (Leave blank to skip) ---
Promotion : 
Original Price : 
Restaurant Name : 
Phone Number : 
Address : 
Website : 
Facebook : 
Instagram : 
Telegram : 
Delivery Platform : 
Opening Hours : 
Call To Action : """

def parse_form_text(text: str) -> dict:
    """Parses key-value pairs from the user's submitted form text."""
    details = {}
    # Mapping of human-readable form labels to dictionary keys
    key_mapping = {
        "food name": "food_name",
        "current price": "price",
        "theme color": "theme_color",
        "promotion": "promotion",
        "original price": "original_price",
        "restaurant name": "restaurant_name",
        "phone number": "phone",
        "address": "address",
        "website": "website",
        "facebook": "facebook",
        "instagram": "instagram",
        "telegram": "telegram",
        "delivery platform": "delivery_platform",
        "opening hours": "opening_hours",
        "call to action": "call_to_action"
    }
    
    for line in text.split('\n'):
        if ':' in line and not line.strip().startswith('---'):
            parts = line.split(':', 1)
            raw_key = parts[0].strip().lower()
            value = parts[1].strip()
            
            # If the field is filled out and matches a known label
            if value and raw_key in key_mapping:
                details[key_mapping[raw_key]] = value
                
    return details

async def start_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the AI Poster Generation sequence."""
    user_id = str(update.effective_user.id)
    balance = get_balance(user_id)
    price = get_poster_price()
    
    if balance < price:
        await update.message.reply_text(
            f"❌ You don't have enough tokens (Need {price}, Have {balance}).\n"
            "Please contact the administrator to purchase more."
        )
        return ConversationHandler.END

    context.user_data['poster_state'] = {'details': {}}
    await update.message.reply_text("Please upload your food image for the poster.")
    return UPLOADING_PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the photo file ID and presents template options."""
    file_id = update.message.photo[-1].file_id
    context.user_data['poster_state']['photo_id'] = file_id
    
    keyboard = [
        [InlineKeyboardButton("✨ Minimal Premium", callback_data="minimal")],
        [InlineKeyboardButton("🔥 Promotion Sale", callback_data="promotion")],
        [InlineKeyboardButton("☕ Cafe Natural", callback_data="cafe_natural")]
    ]
    await update.message.reply_text("Choose your poster style:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_TEMPLATE

async def handle_template_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves chosen template type and sends the form template."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['poster_state']['template'] = query.data
    
    # Send the form for the user to copy and paste
    await query.edit_message_text(f"✅ Selected Style: **{query.data.replace('_', ' ').title()}**\n\n{FORM_TEMPLATE}", parse_mode="Markdown")
    return WAITING_FOR_FORM

async def handle_form_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the submitted form and triggers image generation immediately."""
    state = context.user_data.get('poster_state')
    if not state:
        await update.message.reply_text("❌ Session expired. Please restart by clicking 🎨 AI Poster.")
        return ConversationHandler.END
        
    text_input = update.message.text
    parsed_details = parse_form_text(text_input)
    
    # Validate required fields
    required = ["food_name", "price", "theme_color"]
    missing = [req.replace('_', ' ').title() for req in required if req not in parsed_details]
    
    if missing:
        await update.message.reply_text(
            f"❌ Missing required fields: **{', '.join(missing)}**.\n"
            "Please copy the form again, make sure to fill in those fields, and resend it!",
            parse_mode="Markdown"
        )
        return WAITING_FOR_FORM # Keep waiting for valid form
        
    state['details'] = parsed_details
    return await finalize_generation(update, context)

async def cancel_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Forced exit routing clearing existing allocations."""
    context.user_data.pop('poster_state', None)
    msg = "❌ Poster generation session closed."
    if update.callback_query:
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)
    return ConversationHandler.END

async def finalize_generation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Runs data injection through pure REST services cleanly."""
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    state = context.user_data['poster_state']
    price = get_poster_price()
    
    status_msg = await context.bot.send_message(chat_id=chat_id, text="⏳ Generating your poster... Please wait while we process the graphics.")
    
    if not deduct_tokens(user_id, price):
        await status_msg.edit_text("❌ Insufficient token balance available for execution.")
        return ConversationHandler.END

    try:
        # Get image bytes from Telegram
        file = await context.bot.get_file(state['photo_id'])
        img_buffer = io.BytesIO()
        await file.download_to_memory(img_buffer)
        image_bytes = img_buffer.getvalue()

        # Step 1: Vision analysis via clean backend routes
        food_desc = await analyze_and_prompt(image_bytes, state['details'])
        
        # Step 2: Combine base structure with selected theme layout
        structured_prompt = build_poster_prompt(state['details'], state['template'], food_desc)
        
        # Step 3: Call Imagen 4.0 engine
        final_render = await generate_poster_image(structured_prompt)
        
        # Deliver production file to frontend client space
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=final_render,
            caption="✅ Asset generated successfully matching design requirements!"
        )
        save_poster_history(user_id, 1, state['photo_id'], "SUCCESSFUL_REST_RENDER", price, "SUCCESS")
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Render runtime tracking fault identified: {e}")
        add_tokens(user_id, price) # Rollback transactions
        save_poster_history(user_id, 1, state['photo_id'], "REST_FAULT_ABORT", 0, "FAILED")
        await context.bot.send_message(chat_id=chat_id, text="❌ Production pipeline failure encountered. Tokens have been refunded.")
        
    context.user_data.pop('poster_state', None)
    return ConversationHandler.END

# THIS NAME MUST MATCH WHAT YOUR APP.PY IS IMPORTING
poster_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^🎨 AI Poster$'), start_poster)],
    states={
        UPLOADING_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        SELECTING_TEMPLATE: [CallbackQueryHandler(handle_template_selection, pattern="^(minimal|promotion|cafe_natural)$")],
        WAITING_FOR_FORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_form_submission)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_poster),
        MessageHandler(filters.Regex('^❌ Cancel$'), cancel_poster)
    ],
    per_message=False
)