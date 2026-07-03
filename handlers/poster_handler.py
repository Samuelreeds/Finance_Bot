from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from services.ai_service import analyze_and_prompt, generate_poster_image

# States
PHOTO, DETAILS = range(2)

async def start_poster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please upload the food photo for your poster.")
    return PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    context.user_data['poster_image'] = bytes(image_bytes)
    
    await update.message.reply_text(
        "Photo received! Now send me the details in this format:\n\n"
        "Food Name: ...\n"
        "Promotion: ...\n"
        "Price: ...\n"
        "Theme Color: ..."
    )
    return DETAILS

async def receive_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Parsing text input (simplified logic for production)
    text = update.message.text
    context.user_data['poster_details'] = {'raw_text': text} # In production, use regex parser
    
    await update.message.reply_text("Generating poster... this may take a moment.")
    
    try:
        prompt = await analyze_and_prompt(context.user_data['poster_image'], context.user_data['poster_details'])
        image_bytes = await generate_poster_image(prompt)
        
        await update.message.reply_photo(
            photo=image_bytes,
            caption="✅ Your premium poster is ready!"
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        await update.message.reply_text("❌ Generation failed. Please try again.")
        
    return ConversationHandler.END

poster_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^🎨 AI Poster$'), start_poster)],
    states={
        PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
        DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_details)]
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
)