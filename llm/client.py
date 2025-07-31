import json
import re
import ssl
import aiohttp
import certifi
from typing import List, Dict, Any
from llm.tools.calculator import calculate
from llm.functions import functions_schema

OPENROUTER_API_KEY = None  # set externally or injected
MODEL_ID = 'deepseek/deepseek-chat-v3-0324:free'

class LLMClient:
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

        self.tools = functions_schema

    async def handle_function_call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        if function_name == "calculate":
            expression = arguments.get("expression", "")
            return calculate(expression)
        else:
            return "Unknown function"

    async def get_ai_response(self, messages: List[Dict]) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://telegram-bot.local",
            "X-Title": "Telegram Bot"
        }

        api_messages = [{"role": "system", "content": self.system_prompt}]
        api_messages.extend(messages)

        last_message = messages[-1]["content"].lower() if messages else ""
        needs_calculation = any(word in last_message for word in [
            "calculate", "math", "what's", "whats", "+", "-", "*", "/", "=",
            "sqrt", "sin", "cos", "tan", "log", "exp", "factorial", "^", "solve"
        ])

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

                        if self._has_deepseek_tool_call(content):
                            return await self._handle_deepseek_tool_call(content, session, headers, api_messages)

                        message = data["choices"][0]["message"]
                        if message.get("tool_calls"):
                            return await self._handle_tool_calls(session, url, headers, api_messages, message)

                        return content
                    else:
                        print(f"API Error: {response.status}")
                        error_text = await response.text()
                        print(f"Error details: {error_text}")
                        return "sorry something went wrong with my brain rn 605"

        except asyncio.TimeoutError:
            print("Request timed out")
            return "oops that took too long, try again? 550"
        except Exception as e:
            print(f"Error calling API: {e}")
            return "oops my connection is being weird, try again?"

    async def _handle_tool_calls(self, session, url, headers, api_messages, message):
        try:
            tool_messages = api_messages.copy()
            tool_messages.append(message)  # Add the AI's tool call message

            for tool_call in message["tool_calls"]:
                function_name = tool_call["function"]["name"]
                try:
                    function_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    function_args = {"expression": "0"}

                function_result = await self.handle_function_call(function_name, function_args)

                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": function_result
                })

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
                    return "hmm something went wrong with my calculations 914"
        except Exception as e:
            print(f"Tool handling error: {e}")
            return "had trouble with that calculation, but the answer should be there!"

    def _has_deepseek_tool_call(self, content: str) -> bool:
        patterns = [
            r'<｜tool▁call▁begin｜>',
            r'<｜tool▁sep｜>',
            r'function<｜tool▁sep｜>',
            r'<\|tool_call_begin\|>',
            r'<\|tool_sep\|>'
        ]
        return any(re.search(pattern, content) for pattern in patterns)

    async def _handle_deepseek_tool_call(self, content: str, session, headers, api_messages):
        try:
            function_match = re.search(r'function<｜tool▁sep｜>(\w+)', content)
            if not function_match:
                function_match = re.search(r'<\|tool_sep\|>(\w+)', content)

            if function_match:
                function_name = function_match.group(1)

                json_match = re.search(r'json\s*(\{.*?\})', content, re.DOTALL)
                if json_match:
                    try:
                        arguments = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        expr_match = re.search(r'"expression":\s*"([^"]+)"', content)
                        if expr_match:
                            arguments = {"expression": expr_match.group(1)}
                        else:
                            arguments = {}

                    if function_name == "calculate":
                        result = await self.handle_function_call(function_name, arguments)
                        result_message = f"hey! the answer is {result} |||let me know if you need anything else!"
                        return result_message

            return await self._fallback_manual_calc(content)

        except Exception as e:
            print(f"Error handling DeepSeek tool call: {e}")
            return await self._fallback_manual_calc(content)

    async def _fallback_manual_calc(self, content: str):
        if hasattr(self, '_last_user_message'):
            calc_result = self._extract_and_calculate(self._last_user_message)
            if calc_result:
                return f"the answer is {calc_result}! |||hope that helps 60A"

        cleaned = self._clean_response(content)
        return cleaned if cleaned else "hmm something went wrong with that calculation 914"

    def _extract_and_calculate(self, message: str) -> str:
        import re

        patterns = [
            r'\(([\d\+\-\*\/\^\.]+)\)\s*\*\s*([\d\^]+)',
            r'([\d\+\-\*\/\^\.()]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, message)
            for match in matches:
                if isinstance(match, tuple):
                    expr = ''.join(match)
                else:
                    expr = match

                if any(op in expr for op in ['+', '-', '*', '/', '^', '(', ')']):
                    result = calculate(expr)
                    if not result.startswith("Error"):
                        return result

        return None

    def _clean_response(self, content: str) -> str:
        content = re.sub(r'<｜.*?｜>', '', content)
        content = re.sub(r'function<｜.*?｜>', '', content)
        content = re.sub(r'json\s*\{.*?\}', '', content, flags=re.DOTALL)
        content = re.sub(r'ちょ.*?function', '', content)
        content = re.sub(r'<\|.*?\|>', '', content)

        content = re.sub(r'\s+', ' ', content).strip()

        return content

    def split_response(self, response: str) -> List[str]:
        parts = response.split("|||")

        messages = []
        for part in parts:
            part = part.strip()
            if part:
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
