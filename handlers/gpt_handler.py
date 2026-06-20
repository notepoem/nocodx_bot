import asyncio
import json
import logging
import os
from typing import Dict, Any
import aiohttp
from urllib.parse import quote
from cleanup import cache_manager
from config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 10
CONVERSATIONS_FILE = "cache/gpt_conversations.json"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

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

async def ask_gpt(bot, prompt: str, chat_id: int) -> Dict[str, Any]:
    history = cache_manager.load_chat_history("gpt", chat_id) or []

    messages = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "content": turn['user']})
        messages.append({"role": "assistant", "content": turn['assistant']})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": messages
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    err_body = await resp.text()
                    logger.error(f"OpenRouter API returned HTTP {resp.status}: {err_body}")
                    return {"status": "error", "error": f"OpenRouter API returned HTTP {resp.status}."}
                data = await resp.json()

        if "choices" in data and len(data["choices"]) > 0:
            answer = data["choices"][0]["message"]["content"].strip()
            history.append({"user": prompt, "assistant": answer})
            if len(history) > MAX_HISTORY_TURNS:
                history.pop(0)
            cache_manager.save_chat_history("gpt", chat_id, history)
            return {"status": "success", "answer": answer}

        return {"status": "error", "error": "No response received from ChatGPT."}
    except Exception as e:
        logger.error(f"GPT Error: {e}")
        return {"status": "error", "error": f"ChatGPT Error: {str(e)}"}

async def is_admin(bot, chat_id, user_id):
    if chat_id > 0: return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit):
    @custom_command_handler("gpt")
    async def handle_gpt(message):
        if not await check_usage_limit(message, "GPT"):
            return

        data_status = load_status()

        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
            prompt_raw = " ".join(parts_split[1:]).strip()
        else:
            prompt_raw = ""

        if not prompt_raw:
            await bot.reply_to(message, "❓ Usage: `/gpt [your question]`", parse_mode="Markdown")
            return

        thinking_msg = await bot.reply_to(message, "🤖 ChatGPT is thinking...")

        try:
            result = await ask_gpt(bot, prompt_raw, message.chat.id)

            hint = ""
            if message.chat.type == "private" and message.from_user.id not in data_status.get("hints_shown", []):
                hint = f"\n\n💡 <b>Tip:</b> Use /ongpt to enable conversational mode and /offgpt to reset context."
                data_status["hints_shown"].append(message.from_user.id)
                save_status(data_status)

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            final_text = (
                f"🤖 <b>𝗖𝗵𝗮𝘁𝗚𝗣𝗧 𝗔𝗜:</b>\n•──────────────────────•\n{result['answer']}{hint}\n{footer}"
                if result['status'] == 'success' else f"❌ {result['error']}"
            )
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=final_text, parse_mode="HTML")
        except Exception as e:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=f"❌ Error: {str(e)}")

    @custom_command_handler("ongpt")
    async def enable_gpt(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id): return
        data = load_status()
        data["auto_reply"][str(message.chat.id)] = True
        save_status(data)
        await bot.reply_to(message, "✅ ChatGPT auto-reply has been enabled.")

    @custom_command_handler("offgpt")
    async def disable_gpt(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id): return
        data = load_status()
        data["auto_reply"][str(message.chat.id)] = False
        save_status(data)
        cache_manager.delete_chat_history("gpt", message.chat.id)
        await bot.reply_to(message, "❌ ChatGPT auto-reply has been disabled.")

    @bot.message_handler(func=lambda message: message.text and str(message.chat.id) in load_status()["auto_reply"] and load_status()["auto_reply"][str(message.chat.id)])
    async def auto_reply_gpt(message):
        if any(message.text.lower().startswith(prefix) for prefix in command_prefixes_list):
            return

        is_group = message.chat.type in ["group", "supergroup"]
        is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id
        is_mentioned = f"@{(await bot.get_me()).username.lower()}" in message.text.lower()

        if is_group and not (is_reply_to_me or is_mentioned):
            return

        thinking_msg = await bot.reply_to(message, "🤖 Thinking...")
        try:
            result = await ask_gpt(bot, message.text, message.chat.id)
            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            final_text = (
                f"🤖 <b>𝗖𝗵𝗮𝘁𝗚𝗣𝗧 𝗔𝗜:</b>\n•──────────────────────•\n{result['answer']}\n{footer}"
                if result['status'] == 'success' else f"❌ {result['error']}"
            )
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=final_text, parse_mode="HTML")
        except Exception as e:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=thinking_msg.message_id, text=f"❌ Error: {str(e)}")
