import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ORDER_TOPIC_ID = os.getenv("ORDER_TOPIC_ID")
EXPENSE_TOPIC_ID = os.getenv("EXPENSE_TOPIC_ID")
INCOME_TOPIC_ID = os.getenv("INCOME_TOPIC_ID")
# Add this alongside your other topic IDs
REPORT_TOPIC_ID = os.getenv("REPORT_TOPIC_ID")

# NEW: Delivery Fee Configuration
DELIVERY_FEE = 2.0

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables.")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables.")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables.")