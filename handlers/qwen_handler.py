import asyncio
import logging
import re
import os
from typing import Dict, Any
from groq import AsyncGroq
from cleanup import cache_manager

logger = logging.getLogger(__name__)

from config import GROQ_API_KEY
MODEL_NAME = "qwen/qwen3-32b"
SYSTEM_PROMPT = "You are a caring chatbot. Your answers should be concise and brief. Respond in the same language the user speaks."
MAX_HISTORY_TURNS = 10
CONVERSATIONS_FILE = "cache/qwen_conversations.json"

def load_status():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"hints_shown": [], "auto_reply": {}}
    return {"hints_shown": [], "auto_reply": {}}

def save_status(data):
    os.makedirs(os.path.dirname(CONVERSATIONS_FILE), exist_ok=True)
    try:
        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

import json
client = AsyncGroq(api_key=GROQ_API_KEY)

def clean_response(text: str) -> str:
    """উত্তরের ভেতর থেকে <think> ব্লক রিমুভ করে।"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def format_history_for_groq(history: list, new_prompt: str) -> list:
    """হিস্ট্রিকে Groq মেসেজ ফরম্যাটে রূপান্তর করে।"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        messages.append({"role": "user", "content": turn['user']})
        messages.append({"role": "assistant", "content": turn['assistant']})
    messages.append({"role": "user", "content": new_prompt})
    return messages

async def ask_qwen(bot, prompt: str, chat_id: int) -> Dict[str, Any]:
    history = cache_manager.load_chat_history("qwen", chat_id) or []
    messages = format_history_for_groq(history, prompt)

    try:
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.6,
            max_completion_tokens=4096,
            top_p=0.95,
            stream=False
        )

        raw_text = completion.choices[0].message.content or ""
        qwen_response_text = clean_response(raw_text)

        if qwen_response_text:
            history.append({"user": prompt, "assistant": qwen_response_text})
            if len(history) > MAX_HISTORY_TURNS:
                history.pop(0)

            cache_manager.save_chat_history("qwen", chat_id, history)

            return {
                'status': 'success',
                'answer': qwen_response_text
            }

        return {'status': 'error', 'error': "No response from Qwen API "}
    except Exception as e:
        logger.error(f"Qwen Error: {e}")
        return {'status': 'error', 'error': f'Qwen AI Error: {str(e)}'}

async def is_admin(bot, chat_id, user_id):
    if chat_id > 0: return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("qwen", "qn")
    async def handle_qwen(message):
        if check_usage_limit and not await check_usage_limit(message, "Qwen"):
            return
        
        data_status = load_status()
        
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             prompt_raw = " ".join(parts_split[1:]).strip()
        else:
             prompt_raw = ""

        if not prompt_raw:
            await bot.reply_to(message, f"❓ Uses: `{command_used} [Your Question]`", parse_mode="Markdown")
            return

        thinking_msg = await bot.reply_to(message, "🤖 Qwen is Thinking...")

        try:
            result = await ask_qwen(bot, prompt_raw, message.chat.id)
            
            hint = ""
            if message.chat.type == "private" and message.from_user.id not in data_status.get("hints_shown", []):
                hint = f"\n\n💡 <b>Tip:</b> Use /onqwen to enable conversational mode and /offqwen to reset context."
                data_status["hints_shown"].append(message.from_user.id)
                save_status(data_status)

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
            
            final_text = f"🤖 <b>𝗤𝘄𝗲𝗻 𝗔𝗜:</b>\n•──────────────────────•\n{result['answer']}{hint}\n{footer}" if result['status'] == 'success' else f"❌ {result['error']}"
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=final_text, parse_mode="HTML")
        except Exception as e:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=f"❌ ত্রুটি: {str(e)}")

    @custom_command_handler("onqwen", "onqn")
    async def enable_qwen(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id): return
        data = load_status()
        data["auto_reply"][str(message.chat.id)] = True
        save_status(data)
        await bot.reply_to(message, "✅ Qwen Auto Reoly ON")

    @custom_command_handler("offqwen", "offqn")
    async def disable_qwen(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id): return
        data = load_status()
        data["auto_reply"][str(message.chat.id)] = False
        save_status(data)
        cache_manager.delete_chat_history("qwen", message.chat.id)
        await bot.reply_to(message, "❌ Qwen Auto Reoly OFF")

    @bot.message_handler(func=lambda message: message.text and str(message.chat.id) in load_status()["auto_reply"] and load_status()["auto_reply"][str(message.chat.id)])
    async def auto_reply_qwen(message):
        if any(message.text.lower().startswith(prefix) for prefix in command_prefixes_list):
            return

        is_group = message.chat.type in ["group", "supergroup"]
        is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id
        is_mentioned = f"@{(await bot.get_me()).username.lower()}" in message.text.lower()

        if is_group and not (is_reply_to_me or is_mentioned):
            return

        thinking_msg = await bot.reply_to(message, "🤖 Qwen is Thinking...")
        try:
            result = await ask_qwen(bot, message.text, message.chat.id)
            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
            
            final_text = f"🤖 <b>𝗤𝘄𝗲𝗻 𝗔𝗜:</b>\n•──────────────────────•\n{result['answer']}\n{footer}" if result['status'] == 'success' else f"❌ {result['error']}"
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=final_text, parse_mode="HTML")
        except Exception as e:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=f"❌ ত্রুটি: {str(e)}")
