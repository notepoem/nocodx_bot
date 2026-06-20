import os
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, Union
import json
from cleanup import cache_manager

logger = logging.getLogger(__name__)

CONVERSATIONS_FILE = "cache/grok_conversations.json"

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

GROK_API_URL = "https://x-ai-nu.vercel.app/grok3?ask={}"

SYSTEM_PROMPT = "You are a caring chatbot. Your answers should be concise and brief. Respond in the same language the user speaks."

MAX_HISTORY_TURNS = 10

def get_full_prompt(history: list, new_prompt: str) -> str:
    full_prompt = SYSTEM_PROMPT
    for turn in history:
        full_prompt += f"\n\nuser: {turn['user']}\nassistant: {turn['assistant']}"
    full_prompt += f"\n\nuser: {new_prompt}\nassistant:"
    return full_prompt

async def ask_grok(bot, prompt: str, chat_id: int) -> Dict[str, Any]:
    history = cache_manager.load_chat_history("grok", chat_id) or []

    full_prompt = get_full_prompt(history, prompt)

    encoded_prompt = aiohttp.helpers.quote(full_prompt)
    api_url = GROK_API_URL.format(encoded_prompt)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as res:
                res.raise_for_status()
                data = await res.json()

                if data and data.get("reply"):
                    grok_response_text = data.get("reply")

                    history.append({"user": prompt, "assistant": grok_response_text})

                    if len(history) > MAX_HISTORY_TURNS:
                        history.pop(0)

                    cache_manager.save_chat_history("grok", chat_id, history)
                    
                    return {
                        'status': 'success',
                        'answer': grok_response_text
                    }

                return {
                    'status': 'error',
                    'error': data.get("reply", "No response from API.")
                }
    except Exception as e:
        logger.error(f"Error asking Grok: {e}")
        return {
            'status': 'error',
            'error': f'Grok error: {str(e)}'
        }

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
    @custom_command_handler("grok")
    async def handle_grok(message):
        if check_usage_limit and not await check_usage_limit(message, "Grok"):
            return
        
        data_status = load_status()
        
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             user_input = " ".join(parts_split[1:]).strip()
        else:
             user_input = ""

        if not user_input:
            await bot.reply_to(message, f"❓ `{command_prefixes_list[0]}grok [question]` - Example: `{command_prefixes_list[0]}grok How are you?`", parse_mode="Markdown")
            return

        thinking_message = await bot.reply_to(message, "🤖 Grok thinking...")

        try:
            result = await ask_grok(bot, user_input, message.chat.id)

            if result['status'] == 'success':
                hint = ""
                if message.chat.type == "private" and message.from_user.id not in data_status.get("hints_shown", []):
                    hint = f"\n\n💡 <b>Tip:</b> Use /ongrok to enable conversational mode and /offgrok to reset context."
                    data_status["hints_shown"].append(message.from_user.id)
                    save_status(data_status)

                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"🤖 <b>𝗚𝗿𝗼𝗸 𝗔𝗜:</b>\n•──────────────────────•\n{result['answer']}{hint}\n{footer}",
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

    @custom_command_handler("ongrok")
    async def enable_grok_autoreply(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await bot.reply_to(message, "❌ This command is only for group admins.")
            return

        data = load_status()
        data["auto_reply"][str(message.chat.id)] = True
        save_status(data)
        await bot.reply_to(message, "✅ Grok auto-reply enabled.")

    @custom_command_handler("offgrok")
    async def disable_grok_autoreply(message):
        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await bot.reply_to(message, "❌ This command is only for group admins.")
            return

        data = load_status()
        data["auto_reply"][str(message.chat.id)] = False
        save_status(data)
        cache_manager.delete_chat_history("grok", message.chat.id)
        await bot.reply_to(message, "❌ Grok auto-reply disabled and chat history cleared.")

    @bot.message_handler(func=lambda msg: str(msg.chat.id) in load_status()["auto_reply"] and load_status()["auto_reply"][str(msg.chat.id)] and msg.content_type == 'text' and not any(msg.text.lower().startswith(p) for p in command_prefixes_list))
    async def auto_reply_grok(message):
        chat_id = message.chat.id

        is_private = message.chat.type == "private"
        is_reply_to_me = message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id
        is_mentioned = f"@{(await bot.get_me()).username.lower()}" in message.text.lower() if message.text else False

        # If it's a group, only reply if mentioned or if it's a reply to the bot
        if not is_private and not (is_reply_to_me or is_mentioned):
            return

        thinking_message = await bot.reply_to(message, "🤖 Grok thinking...")

        try:
            reply = await ask_grok(bot, message.text, chat_id)

            if reply['status'] == 'success':
                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"🤖 <b>𝗚𝗿𝗼𝗸 𝗔𝗜:</b>\n•──────────────────────•\n{reply['answer']}\n{footer}",
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"❌ Error: {reply['error']}"
                )
        except Exception as e:
            await bot.edit_message_text(
                chat_id=thinking_message.chat.id,
                message_id=thinking_message.message_id,
                text=f"❌ Error: {e}"
            )