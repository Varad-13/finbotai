import asyncio
import re
import random
import ssl
import json
import math
from typing import List, Dict, Any
import aiohttp
import certifi
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
import os

load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = 'deepseek/deepseek-chat-v3-0324:free'

# Store conversation history (in production, use a database)
conversations = {}

class ConversationBot:
    def __init__(self):
        self.system_prompt = """You are a casual, friendly person texting via telegram. Your personality:
- use lowercase letters most of the time (like "hey" not "Hey")
- send multiple short messages instead of one long one
- use slang, abbreviations like "lol", "omg", "tbh", "ngl", etc.
- be conversational and natural
- sometimes use emojis but don't overdo it
- keep individual messages under 50 words when possible
- split longer thoughts into multiple messages
- be helpful but in a casual way

You have access to a calculator tool. Use it when someone asks for math calculations, even simple ones.

Important: Respond with multiple short messages separated by "|||" - each part will be sent as a separate message."""

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform mathematical calculations including basic arithmetic, trigonometry, logarithms, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate (e.g., '2+2', 'sqrt(16)', 'sin(pi/2)', '(5*3)+2')"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            }
        ]

    def calculate(self, expression: str) -> str:
        """Safe calculator function"""
        try:
            # Replace common math functions for eval safety
            safe_dict = {
                "__builtins__": {},
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
                "ceil": math.ceil,
                "floor": math.floor,
                "factorial": math.factorial
            }
            
            # Clean the expression
            expression = expression.replace("^", "**")  # Replace ^ with **
            
            # Evaluate safely
            result = eval(expression, safe_dict)
            return str(result)
            
        except Exception as e:
            return f"Error: {str(e)}"

    async def handle_function_call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Handle function calls from the AI"""
        if function_name == "calculate":
            expression = arguments.get("expression", "")
            result = self.calculate(expression)
            return result
        else:
            return "Unknown function"

    async def get_ai_response(self, messages: List[Dict]) -> str:
        """Get response from OpenRouter API with DeepSeek tool call handling"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-bot.local",
            "X-Title": "Telegram Bot"
        }
        
        # Prepare messages for API
        api_messages = [{"role": "system", "content": self.system_prompt}]
        api_messages.extend(messages)
        
        # Check if the last message seems to need calculation
        last_message = messages[-1]["content"].lower() if messages else ""
        needs_calculation = any(word in last_message for word in [
            "calculate", "math", "what's", "whats", "+", "-", "*", "/", "=", 
            "sqrt", "sin", "cos", "tan", "log", "exp", "factorial", "^", "solve"
        ])
        
        # Use tools if it needs calculation
        payload = {
            "model": MODEL_ID,
            "messages": api_messages,
            "temperature": 0.8,
            "max_tokens": 300,
            "stream": False
        }
        
        if needs_calculation:
            payload.update({
                "tools": self.tools,
                "tool_choice": "auto"
            })
        
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_OPTIONAL
            connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10, limit_per_host=5)
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        # Check for DeepSeek's custom tool call format
                        if self._has_deepseek_tool_call(content):
                            return await self._handle_deepseek_tool_call(content, session, headers, api_messages)
                        
                        # Check for standard OpenAI tool calls
                        message = data["choices"][0]["message"]
                        if message.get("tool_calls"):
                            return await self._handle_tool_calls(session, url, headers, api_messages, message)
                        
                        return content
                    else:
                        print(f"API Error: {response.status}")
                        error_text = await response.text()
                        print(f"Error details: {error_text}")
                        return "sorry something went wrong with my brain rn 😅"
                        
        except asyncio.TimeoutError:
            print("Request timed out")
            return "oops that took too long, try again? 🕐"
        except Exception as e:
            print(f"Error calling API: {e}")
            return "oops my connection is being weird, try again?"

    async def _handle_tool_calls(self, session, url, headers, api_messages, message):
        """Handle tool calls separately to avoid generator issues"""
        try:
            tool_messages = api_messages.copy()
            tool_messages.append(message)  # Add the AI's tool call message
            
            # Process each tool call
            for tool_call in message["tool_calls"]:
                function_name = tool_call["function"]["name"]
                try:
                    function_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    function_args = {"expression": "0"}  # fallback
                
                # Execute the function
                function_result = await self.handle_function_call(function_name, function_args)
                
                # Add function result to messages
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": function_result
                })
            
            # Get final response from AI with function results
            final_payload = {
                "model": MODEL_ID,
                "messages": tool_messages,
                "temperature": 0.8,
                "max_tokens": 300,
                "stream": False
            }
            
            async with session.post(url, headers=headers, json=final_payload) as final_response:
                if final_response.status == 200:
                    final_data = await final_response.json()
                    return final_data["choices"][0]["message"]["content"]
                else:
                    return "hmm something went wrong with my calculations 🤔"
        except Exception as e:
            print(f"Tool handling error: {e}")
            return "had trouble with that calculation, but the answer should be there!"

    def _has_deepseek_tool_call(self, content: str) -> bool:
        """Check if content contains DeepSeek's tool call format"""
        patterns = [
            r'<｜tool▁call▁begin｜>',
            r'<｜tool▁sep｜>',
            r'function<｜tool▁sep｜>',
            r'<\|tool_call_begin\|>',
            r'<\|tool_sep\|>'
        ]
        return any(re.search(pattern, content) for pattern in patterns)
    
    async def _handle_deepseek_tool_call(self, content: str, session, headers, api_messages):
        """Handle DeepSeek's custom tool call format"""
        try:
            # Extract function name and arguments from DeepSeek format
            function_match = re.search(r'function<｜tool▁sep｜>(\w+)', content)
            if not function_match:
                function_match = re.search(r'<\|tool_sep\|>(\w+)', content)
            
            if function_match:
                function_name = function_match.group(1)
                
                # Extract JSON arguments
                json_match = re.search(r'json\s*(\{.*?\})', content, re.DOTALL)
                if json_match:
                    try:
                        arguments = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        # Try to extract expression manually
                        expr_match = re.search(r'"expression":\s*"([^"]+)"', content)
                        if expr_match:
                            arguments = {"expression": expr_match.group(1)}
                        else:
                            arguments = {}
                    
                    # Execute the function
                    if function_name == "calculate":
                        result = await self.handle_function_call(function_name, arguments)
                        
                        # Create a new request with the result
                        result_message = f"hey! the answer is {result} |||let me know if you need anything else!"
                        return result_message
            
            # If we can't parse it, try to extract the math expression manually
            return await self._fallback_manual_calc(content)
            
        except Exception as e:
            print(f"Error handling DeepSeek tool call: {e}")
            return await self._fallback_manual_calc(content)
    
    async def _fallback_manual_calc(self, content: str):
        """Fallback to manual calculation if tool parsing fails"""
        # Look for math expressions in the original request
        if hasattr(self, '_last_user_message'):
            calc_result = self._extract_and_calculate(self._last_user_message)
            if calc_result:
                return f"the answer is {calc_result}! |||hope that helps 😊"
        
        # Clean the response and return it
        cleaned = self._clean_response(content)
        return cleaned if cleaned else "hmm something went wrong with that calculation 🤔"

    def _extract_and_calculate(self, message: str) -> str:
        """Extract math expressions and calculate them manually"""
        import re
        
        # Common math patterns
        patterns = [
            r'\(([\d\+\-\*\/\^\.]+)\)\s*\*\s*([\d\^]+)',  # (5+3) * 2^3
            r'([\d\+\-\*\/\^\.()]+)',  # Any math expression
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, message)
            for match in matches:
                if isinstance(match, tuple):
                    expr = ''.join(match)
                else:
                    expr = match
                
                # Only try if it looks like math
                if any(op in expr for op in ['+', '-', '*', '/', '^', '(', ')']):
                    result = self.calculate(expr)
                    if not result.startswith("Error"):
                        return result
        
        return None

    def _clean_response(self, content: str) -> str:
        """Clean up any tool call artifacts from the response"""
        # Remove DeepSeek's tool call syntax
        content = re.sub(r'<｜.*?｜>', '', content)
        content = re.sub(r'function<｜.*?｜>', '', content)
        content = re.sub(r'json\s*\{.*?\}', '', content, flags=re.DOTALL)
        content = re.sub(r'ちょ.*?function', '', content)
        content = re.sub(r'<\|.*?\|>', '', content)
        
        # Clean up extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content

    def split_response(self, response: str) -> List[str]:
        """Split AI response into multiple messages"""
        # Split by our delimiter first
        parts = response.split("|||")
        
        # Clean up each part
        messages = []
        for part in parts:
            part = part.strip()
            if part:
                # Further split long messages at sentence boundaries
                if len(part) > 100:
                    sentences = re.split(r'[.!?]+', part)
                    current_msg = ""
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                        if len(current_msg + sentence) > 80 and current_msg:
                            messages.append(current_msg.strip())
                            current_msg = sentence
                        else:
                            current_msg += (" " + sentence if current_msg else sentence)
                    if current_msg:
                        messages.append(current_msg.strip())
                else:
                    messages.append(part)
        
        return messages if messages else [response]

bot = ConversationBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    conversations[user_id] = []
    
    await update.message.reply_text("hey! 👋 i'm here to chat")
    await asyncio.sleep(0.5)
    await update.message.reply_text("just message me anything and we can talk!")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("cleared our chat history 🧹")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages with better error handling"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Store last user message for fallback calculations
    bot._last_user_message = user_message
    
    # Initialize conversation if doesn't exist
    if user_id not in conversations:
        conversations[user_id] = []
    
    # Add user message to history
    conversations[user_id].append({"role": "user", "content": user_message})
    
    # Limit conversation history (keep last 15 messages for better performance)
    if len(conversations[user_id]) > 15:
        conversations[user_id] = conversations[user_id][-15:]
    
    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        # Get AI response
        ai_response = await bot.get_ai_response(conversations[user_id])
        
        # Add AI response to history
        conversations[user_id].append({"role": "assistant", "content": ai_response})
        
        # Split response into multiple messages
        message_parts = bot.split_response(ai_response)
        
        # Send messages with realistic delays
        for i, part in enumerate(message_parts):
            if i > 0:
                # Show typing between messages
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                # Random delay between messages (0.5 to 2 seconds)
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            await update.message.reply_text(part)
            
    except Exception as e:
        print(f"Error in handle_message: {e}")
        await update.message.reply_text("oops something went wrong! try again? 😅")

async def tools_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available tools"""
    tools_text = """🛠️ my tools:
🧮 calculator - i can do math! try asking me things like:
  • "what's 25 * 47?"
  • "calculate sqrt(144)"
  • "what's sin(pi/2)?"
  • "solve (5+3) * 2^3"

just ask me naturally and i'll use the right tool! ✨"""
    
    await update.message.reply_text(tools_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """available commands:
/start - start chatting
/clear - clear our conversation history
/tools - see what tools i can use
/help - show this message

just send me any message to chat! 💬
i can also do math calculations - just ask naturally! 🧮"""
    
    await update.message.reply_text(help_text)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by Updates."""
    print(f"Update {update} caused error {context.error}")

def main():
    """Main function to run the bot"""
    # Create application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CommandHandler("tools", tools_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("bot starting...")
    print("press ctrl+c to stop")
    
    # Run the bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()