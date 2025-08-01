import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI
from config import BOT_TOKEN, OPENROUTER_API_KEY, MODEL
from tools import TOOL_MAPPING
from tools_def import tools
from models import save_message_orm, get_all_messages_orm

logging.basicConfig(level=logging.WARNING)  # Changed from INFO to WARNING to reduce spam logs

openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    system_prompt = """
        You are an onboarding assistant for Fridayy.
        You must authenticate the user with their phone number, then register their store based on business categories.
    """

    # Retrieve full conversation history from DB
    conversation_history = get_all_messages_orm()

    messages = [{"role": "system", "content": system_prompt}]

    # Append conversation history messages except system prompt (avoid duplicate system prompt)
    for msg in conversation_history:
        if msg.role == "system":
            continue
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_input})

    save_message_orm("user", user_input)

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    assistant_message = response.choices[0].message

    save_message_orm("assistant", assistant_message.content if hasattr(assistant_message, 'content') else str(assistant_message))

    if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
        tool_call = assistant_message.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        tool_result = TOOL_MAPPING[tool_name](**tool_args)

        messages.append(assistant_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": json.dumps(tool_result),
        })

        save_message_orm("tool", json.dumps(tool_result))

        final_response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
        )
        final_text = final_response.choices[0].message.content
        await update.message.reply_text(final_text)
    else:
        await update.message.reply_text(assistant_message.content or "I didn't understand that.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()
