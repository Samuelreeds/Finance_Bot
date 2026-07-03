import os
from telegram import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
ADMIN_CHAT_ID = str(os.getenv("ADMIN_CHAT_ID"))

def get_main_menu_keyboard(user_id: int | str) -> ReplyKeyboardMarkup:
    """Returns a dynamic keyboard menu based on user permissions."""
    
    # 1. Base Menu (Visible to EVERYONE)
    keyboard = [
        [KeyboardButton("📝 New Order"), KeyboardButton("🎨 AI Poster")],
        [KeyboardButton("📉 Expense"), KeyboardButton("📈 Income")],
        [KeyboardButton("📊 Report")]
    ]
    
    # 2. Admin Menu (Appended ONLY if the ID matches yours)
    if str(user_id) == ADMIN_CHAT_ID:
        admin_row_1 = [KeyboardButton("📦 Inventory"), KeyboardButton("👥 Customers")]
        admin_row_2 = [KeyboardButton("⚙️ System Settings"), KeyboardButton("🪙 Token Manager")]
        
        keyboard.append(admin_row_1)
        keyboard.append(admin_row_2)
        
    return ReplyKeyboardMarkup(
        keyboard, 
        resize_keyboard=True, 
        input_field_placeholder="Select an option from the menu..."
    )