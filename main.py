import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI
from config import BOT_TOKEN, OPENROUTER_API_KEY, MODEL
from tools import TOOL_MAPPING
from tools_def import tools
from models import save_message_orm, get_conversation_messages_orm

logging.basicConfig(level=logging.WARNING)  # To reduce spam logs

openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    # Use chat_id as conversation identifier
    conversation_id = str(update.effective_chat.id)

    system_prompt = """
        You are an onboarding assistant for Fridayy.
        You must authenticate the user with their phone number, then register their store based on business categories.
    """

    # Retrieve full conversation history for this conversation
    conversation_history = get_conversation_messages_orm(conversation_id)

    messages = [{"role": "system", "content": system_prompt}]

    # Append conversation history messages except system prompt
    for msg in conversation_history:
        if msg.role == "system":
            continue
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_input})

    # Save current user message
    save_message_orm(conversation_id, "user", user_input)

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    assistant_message = response.choices[0].message

    # Save assistant message
    save_message_orm(conversation_id, "assistant", assistant_message.content if hasattr(assistant_message, 'content') else str(assistant_message))

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

        # Save tool result
        save_message_orm(conversation_id, "tool", json.dumps(tool_result))

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
