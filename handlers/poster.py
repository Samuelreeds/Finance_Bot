import os
from telegram import Update
from telegram.ext import ContextTypes
from services.token_service import add_tokens, set_poster_price, get_balance
from services.prompt_service import get_all_prompts, add_prompt, toggle_prompt
from services.database_service import get_connection
from dotenv import load_dotenv

load_dotenv()
ADMIN_CHAT_ID = str(os.getenv("ADMIN_CHAT_ID"))

async def add_tokens_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized. Restricted to administrators.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /addtokens <telegram_id> 100\n(Tip: use '/addtokens me 100' for yourself)")
        return
        
    user_id = args[0]
    
    # MAGIC TRICK: If you type "me", it automatically grabs your numeric ID!
    if user_id.lower() == "me":
        user_id = str(update.effective_user.id)
        
    try:
        amount = int(args[1])
        add_tokens(user_id, amount)
        await update.message.reply_text(f"✅ Added {amount} tokens. New Balance: {get_balance(user_id)}")
    except ValueError:
        await update.message.reply_text("❌ Amount must be a number.")

async def set_poster_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized. Restricted to administrators.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setposterprice 15")
        return
    try:
        price = int(context.args[0])
        set_poster_price(price)
        await update.message.reply_text(f"✅ Poster generation price set to {price} tokens.")
    except ValueError:
        await update.message.reply_text("❌ Price must be a number.")

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This remains available to everyone so they can check their personal wallet limits.
    user_id = str(update.effective_user.id)
    balance = get_balance(user_id)
    await update.message.reply_text(f"Current Balance\n{balance} Tokens")

async def prompts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized. Restricted to administrators.")
        return

    args = context.args
    
    # Sub-commands for quick management
    if args and args[0] == "add":
        text = " ".join(args[1:])
        if "|" not in text:
            await update.message.reply_text("Usage: /prompts add Name | The prompt description here...")
            return
        name, prompt = text.split("|", 1)
        add_prompt(name.strip(), prompt.strip())
        await update.message.reply_text(f"✅ Prompt '{name.strip()}' added.")
        return
        
    if args and args[0] in ["enable", "disable"]:
        try:
            pid = int(args[1])
            active = 1 if args[0] == "enable" else 0
            toggle_prompt(pid, active)
            await update.message.reply_text(f"✅ Prompt {pid} {'enabled' if active else 'disabled'}.")
        except:
            await update.message.reply_text("Usage: /prompts enable <id>")
        return

    # List prompts
    prompts = get_all_prompts()
    msg = "========================================\nPROMPTS\n========================================\n"
    for p in prompts:
        status = "✅" if p['active'] else "❌"
        msg += f"{p['id']}. {p['name']} {status}\n"
    msg += "========================================\nManage: /prompts add Name | Prompt\n/prompts enable ID\n/prompts disable ID"
    await update.message.reply_text(msg)

async def poster_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized. Restricted to administrators.")
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name, h.created_at, h.tokens_used, h.status 
        FROM poster_history h 
        JOIN poster_prompts p ON h.prompt_id = p.id 
        ORDER BY h.created_at DESC LIMIT 10
    ''')
    history = cursor.fetchall()
    conn.close()
    
    if not history:
        await update.message.reply_text("No poster history found.")
        return
        
    msg = "========================================\nPOSTER HISTORY (Last 10)\n========================================\n"
    for h in history:
        date = h['created_at'].strftime("%Y-%m-%d %H:%M")
        msg += f"[{date}] {h['name']} - {h['tokens_used']} Tokens ({h['status']})\n"
    await update.message.reply_text(msg)