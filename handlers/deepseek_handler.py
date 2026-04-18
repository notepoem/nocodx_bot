import os
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, Union
import json

logger = logging.getLogger(__name__)

CONVERSATIONS_FILE = "cache/deepseek_conversations.json"

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

DEEPSEEK_API_URL = "https://deepseek-r1v3.vercel.app/api/ds-chat-v3-1?q={}"
SYSTEM_PROMPT = "You must detect the language used by the user and respond in that EXACT same language. If the user speaks English, respond in English. If the user speaks Bengali or any other language (even if written in Romanized/English characters like 'kemon aco'), identify that language and respond using its native script."
MAX_HISTORY_TURNS = 10

def get_full_prompt(history: list, new_prompt: str) -> str:
    full_prompt = SYSTEM_PROMPT
    for turn in history:
        full_prompt += f"\n\nuser: {turn['user']}\nassistant: {turn['assistant']}"
    full_prompt += f"\n\nuser: {new_prompt}\nassistant:"
    return full_prompt

async def ask_deepseek(bot, prompt: str, chat_id: int) -> Dict[str, Any]:
    if not hasattr(bot, 'deepseek_histories'):
        bot.deepseek_histories = {}

    if chat_id not in bot.deepseek_histories:
        bot.deepseek_histories[chat_id] = []

    history = bot.deepseek_histories[chat_id]

    full_prompt = get_full_prompt(history, prompt)

    encoded_prompt = aiohttp.helpers.quote(full_prompt)
    api_url = DEEPSEEK_API_URL.format(encoded_prompt)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as res:
                res.raise_for_status()
                data = await res.json()

                if data and data.get("reply"):
                    deepseek_response_text = data.get("reply")

                    history.append({"user": prompt, "assistant": deepseek_response_text})

                    if len(history) > MAX_HISTORY_TURNS:
                        history.pop(0)

                    bot.deepseek_histories[chat_id] = history
                    return {
                        'status': 'success',
                        'answer': deepseek_response_text
                    }

                return {'status': 'error', 'error': "No response was received from Deepseek."}
    except Exception as e:
        logger.error(f"Deepseek Error: {e}")
        return {'status': 'error', 'error': f'Deepseek API Error: {str(e)}'}

async def is_admin(bot, chat_id, user_id):
    if chat_id > 0:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ['administrator', 'creator']:
            return True
    except Exception as e:
        print(f"Error checking admin status: {e}")
    return False

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    if not hasattr(bot, 'deepseek_histories'):
        bot.deepseek_histories = {}

    @custom_command_handler("deepseek", "deep", "ds")
    async def handle_deepseek(message):
        if check_usage_limit and not await check_usage_limit(message, "Deepseek"):
            return
        
        data_status = load_status()
        
        parts_split = message.text.strip().split()
        command_part = parts_split[0] if parts_split else ""
        if len(parts_split) > 1:
             user_input = " ".join(parts_split[1:]).strip()
        else:
             user_input = ""

        if not user_input:
            await bot.reply_to(message, f"❓ Usage: <code>{command_part} [your question]</code>. Example: <code>{command_part} What is a loop in Python?</code>", parse_mode="HTML")
            return

        thinking_message = await bot.reply_to(message, "🤖 Deepseek is thinking...")

        try:
            result = await ask_deepseek(bot, user_input, message.chat.id)

            if result['status'] == 'success':
                hint = ""
                if message.chat.type == "private" and message.from_user.id not in data_status.get("hints_shown", []):
                    hint = f"\n\n💡 <b>Tip:</b> Use /ondeepseek to enable conversational mode and /offdeepseek to reset context."
                    data_status["hints_shown"].append(message.from_user.id)
                    save_status(data_status)

                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"🤖 <b>𝗗𝗲𝗲𝗽𝘀𝗲𝗲𝗸 𝗔𝗜:</b>\n•──────────────────────•\n{result['answer']}{hint}\n{footer}",
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"❌ Error: {result['error']}"
                )
        except Exception as e:
            await bot.edit_message_text(
                chat_id=thinking_message.chat.id,
                message_id=thinking_message.message_id,
                text=f"❌ Error: {e}"
            )

    @custom_command_handler("ondeepseek", "onds")
    async def enable_deepseek_autoreply(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await bot.reply_to(message, "❌ This command can only be used by group administrators.")
            return

        data = load_status()
        data["auto_reply"][str(message.chat.id)] = True
        save_status(data)
        await bot.reply_to(message, "✅ Deepseek auto-reply has been enabled.")

    @custom_command_handler("offdeepseek", "offds")
    async def disable_deepseek_autoreply(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await bot.reply_to(message, "❌ This command can only be used by group administrators.")
            return

        data = load_status()
        data["auto_reply"][str(message.chat.id)] = False
        save_status(data)
        if message.chat.id in bot.deepseek_histories:
            del bot.deepseek_histories[message.chat.id]
        await bot.reply_to(message, "❌ Deepseek auto-reply has been disabled and chat history cleared.")

    @bot.message_handler(func=lambda msg: str(msg.chat.id) in load_status()["auto_reply"] and load_status()["auto_reply"][str(msg.chat.id)] and msg.content_type == 'text' and not any(msg.text.lower().startswith(p) for p in command_prefixes_list))
    async def auto_reply_deepseek(message):
        chat_id = message.chat.id

        is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id
        is_group_chat = message.chat.type in ["group", "supergroup"]
        is_at_mentioned = False
        if is_group_chat:
            if f"@{(await bot.get_me()).username.lower()}" in message.text.lower():
                is_at_mentioned = True

        if is_group_chat and not is_reply_to_me and not is_at_mentioned:
            return

        thinking_message = await bot.reply_to(message, "🤖 Deepseek ভাবছে...")

        try:
            reply = await ask_deepseek(bot, message.text, chat_id)

            if reply['status'] == 'success':
                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"🤖 <b>𝗗𝗲𝗲𝗽𝘀𝗲𝗲𝗸 𝗔𝗜:</b>\n•──────────────────────•\n{reply['answer']}\n{footer}",
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"❌ ত্রুটি: {reply['error']}"
                )
        except Exception as e:
            await bot.edit_message_text(
                chat_id=thinking_message.chat.id,
                message_id=thinking_message.message_id,
                text=f"❌ ত্রুটি: {e}"
            )