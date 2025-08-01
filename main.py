import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI
from config import BOT_TOKEN, OPENROUTER_API_KEY, MODEL
from tools import TOOL_MAPPING
from tools_def import tools
from models import save_message_orm, get_conversation_messages_orm

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Initialize OpenAI client for OpenRouter
openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Define system prompt
with open("prompt.md", "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Handler for incoming text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    chat_id = str(update.effective_chat.id)

    # Load conversation history from database
    conversation_history = get_conversation_messages_orm(chat_id)

    # Construct message history with system prompt
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history:
        if msg.role == "system":
            continue

        formatted = {"role": msg.role, "content": msg.content}

        if msg.role == "tool" and msg.tool_call_id:
            # This is the result returned from a tool
            formatted["tool_call_id"] = msg.tool_call_id

        if msg.role == "assistant" and msg.name and msg.tool_call_id:
            # This is a tool call initiated by the assistant
            formatted["tool_calls"] = [
                {
                    "id": msg.tool_call_id,
                    "function": {
                        "name": msg.name,
                        "arguments": msg.content,
                    },
                    "type": "function",
                }
            ]
            # Clear 'content' if it's a tool call, since tool calls don't have normal content
            formatted["content"] = None

        messages.append(formatted)

    # Add current user input
    messages.append({"role": "user", "content": user_input})
    save_message_orm(chat_id, "user", user_input)

    # Call OpenRouter LLM with optional tools
    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    assistant_msg = response.choices[0].message

    # If the model triggers a tool call
    if hasattr(assistant_msg, "tool_calls") and assistant_msg.tool_calls:
        tool_call = assistant_msg.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)
        save_message_orm(
            chat_id,
            role="assistant",
            content=tool_call.function.arguments,  # The tool call arguments JSON string
            name=tool_call.function.name,
            tool_call_id=tool_call.id
        )

        # Call the corresponding tool
        tool_result = TOOL_MAPPING[tool_name](**tool_args)

        # Add assistant + tool call to messages for final completion
        messages.append(assistant_msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": json.dumps(tool_result),
        })

        # Save tool output
        save_message_orm(chat_id, "tool", json.dumps(tool_result), name=tool_name, tool_call_id=tool_call.id)

        # Call LLM again with tool result for final reply
        final_response = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
        )
        final_text = final_response.choices[0].message.content
        save_message_orm(chat_id, "assistant", final_text)
        await update.message.reply_text(final_text)

    else:
        # Normal assistant reply (no tools used)
        reply = assistant_msg.content or "I didn't understand that."
        save_message_orm(chat_id, "assistant", reply)
        await update.message.reply_text(reply)

# Entry point
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()
