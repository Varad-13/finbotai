import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from bot.client import ConversationBot

bot = ConversationBot()
conversations = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    bot._last_user_message = user_message

    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": user_message})

    if len(conversations[user_id]) > 15:
        conversations[user_id] = conversations[user_id][-15:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        ai_response = await bot.get_ai_response(conversations[user_id])

        conversations[user_id].append({"role": "assistant", "content": ai_response})

        message_parts = bot.split_response(ai_response)

        for i, part in enumerate(message_parts):
            if i > 0:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                await asyncio.sleep(random.uniform(0.5, 2.0))
            await update.message.reply_text(part)

    except Exception as e:
        print(f"Error in handle_message: {e}")
        await update.message.reply_text("oops something went wrong! try again? \u001F605")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("hey! \u001F44B i'm here to chat")
    await asyncio.sleep(0.5)
    await update.message.reply_text("just message me anything and we can talk!")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("cleared our chat history \u001F9F9")


async def tools_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tools_text = """6E0\u000FE my tools:
9EE calculator - i can do math! try asking me things like:
  539 "what's 25 * 47?"
  539 "calculate sqrt(144)"
  539 "what's sin(pi/2)?"
  539 "solve (5+3) * 2^3"

just ask me naturally and i'll use the right tool! 496"""
    await update.message.reply_text(tools_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """available commands:
/start - start chatting
/clear - clear our conversation history
/tools - see what tools i can use
/help - show this message

just send me any message to chat! \u001F4AC
i can also do math calculations - just ask naturally! \u001F9EE"""
    await update.message.reply_text(help_text)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error {context.error}")
