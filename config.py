import os
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MODEL = os.getenv("MODEL")  # or gemini/..., anthropic/..., etc.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///message_history.db")  # Default to SQLite if not set