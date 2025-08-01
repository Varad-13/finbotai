import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI
from config import BOT_TOKEN, OPENROUTER_API_KEY, MODEL
from tools import TOOL_MAPPING
from tools_def import tools

logging.basicConfig(level=logging.INFO)

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

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    # Step 1: Ask model what it wants to do
    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    assistant_message = response.choices[0].message
    logging.info(f"Assistant response: {assistant_message}")

    # Step 2: If tool call requested, run tool and send back results
    if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
        tool_call = assistant_message.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        logging.info(f"Calling tool: {tool_name} with args: {tool_args}")

        tool_result = TOOL_MAPPING[tool_name](**tool_args)
        logging.info(f"Tool result: {tool_result}")

        messages.append(assistant_message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": json.dumps(tool_result),
        })

        # Step 3: Finalize response with updated context
        final_response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
        )
        final_text = final_response.choices[0].message.content
        await update.message.reply_text(final_text)
    else:
        # No tool call - just reply with content
        await update.message.reply_text(assistant_message.content or "I didn't understand that.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()
