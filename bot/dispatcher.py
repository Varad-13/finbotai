import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.handlers.message import start, clear_history, handle_message, tools_command, help_command, error_handler

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CommandHandler("tools", tools_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("bot starting...")
    print("press ctrl+c to stop")

    app.run_polling(allowed_updates=None)


if __name__ == "__main__":
    main()
