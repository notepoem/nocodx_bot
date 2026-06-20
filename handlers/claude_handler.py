import requests
from urllib.parse import quote_plus
import json
import os
import asyncio

CONVERSATIONS_FILE = "cache/claude_conversations.json"

def load_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"conversations": {}, "hints_shown": [], "auto_reply": []}
    return {"conversations": {}, "hints_shown": [], "auto_reply": []}

def save_conversations(data):
    os.makedirs(os.path.dirname(CONVERSATIONS_FILE), exist_ok=True)
    try:
        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("claude", "cld")
    async def handle_claude(message):
        if check_usage_limit and not await check_usage_limit(message, "Claude"):
            return
        
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             user_input = " ".join(parts_split[1:]).strip()
        else:
             user_input = ""

        if not user_input:
            await bot.reply_to(
                message, 
                f"❓ Usage: `{command_prefixes_list[0]}claude [prompt]`\n"
                f"Example: `{command_prefixes_list[0]}claude What is your name?`", 
                parse_mode="Markdown"
            )
            return

        thinking_message = await bot.reply_to(message, "🤔 Claude is thinking...")

        data_conv = load_conversations()
        chat_id_str = str(message.chat.id)
        chatid_uuid = data_conv["conversations"].get(chat_id_str)

        try:
            api_url = "https://claude.bbinl.eu.cc/api/claude"
            payload = {"q": user_input}
            if chatid_uuid:
                payload["chatid"] = chatid_uuid
            
            response = await asyncio.to_thread(requests.post, api_url, json=payload, timeout=60)
            response.raise_for_status()
            res_data = response.json()
            
            if res_data.get('response'):
                reply_text = res_data['response']
                new_chatid = res_data.get('chatid')
                
                if chatid_uuid or chat_id_str in data_conv["conversations"]:
                    data_conv["conversations"][chat_id_str] = new_chatid
                    save_conversations(data_conv)

                hint = ""
                if message.chat.type == "private" and message.from_user.id not in data_conv["hints_shown"]:
                    hint = f"\n\n💡 <b>Tip:</b> Use /onclaude to enable conversational mode and /offclaude to reset context."
                    data_conv["hints_shown"].append(message.from_user.id)
                    save_conversations(data_conv)

                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"🤖 <b>𝗖𝗹𝗮𝘂𝗱𝗲 𝗔𝗜:</b>\n•──────────────────────•\n{reply_text}{hint}\n{footer}",
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text="❌ Failed to get response from Claude AI."
                )
            
        except Exception as e:
            try:
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=f"❌ Error: {str(e)}"
                )
            except:
                await bot.reply_to(message, f"❌ Error: {str(e)}")

    @custom_command_handler("onclaude", "oncld")
    async def handle_on_claude(message):
        data_conv = load_conversations()
        chat_id_str = str(message.chat.id)
        user_id = message.from_user.id
        
        changed = False
        if chat_id_str not in data_conv["conversations"]:
            data_conv["conversations"][chat_id_str] = ""
            changed = True
            
        if user_id not in data_conv.get("auto_reply", []):
            if "auto_reply" not in data_conv: data_conv["auto_reply"] = []
            data_conv["auto_reply"].append(user_id)
            changed = True
            
        if changed:
            save_conversations(data_conv)
            await bot.reply_to(message, "✅ Claude Conversational & Auto-reply mode turned <b>ON</b>", parse_mode="HTML")
        else:
            await bot.reply_to(message, "ℹ️ Claude Conversational & Auto-reply mode is already <b>ON</b>", parse_mode="HTML")

    @custom_command_handler("offclaude", "offcld")
    async def handle_off_claude(message):
        data_conv = load_conversations()
        chat_id_str = str(message.chat.id)
        user_id = message.from_user.id
        
        changed = False
        if chat_id_str in data_conv["conversations"]:
            del data_conv["conversations"][chat_id_str]
            changed = True
            
        if user_id in data_conv.get("auto_reply", []):
            data_conv["auto_reply"].remove(user_id)
            changed = True
            
        if changed:
            save_conversations(data_conv)
            await bot.reply_to(message, "⭕ Claude Conversational & Auto-reply turned <b>OFF</b>", parse_mode="HTML")
        else:
            await bot.reply_to(message, "ℹ️ Claude Conversational & Auto-reply is already <b>OFF</b>", parse_mode="HTML")

    @bot.message_handler(func=lambda message: message.text and not any(message.text.startswith(p) for p in command_prefixes_list) and message.from_user.id in load_conversations().get("auto_reply", []))
    async def handle_claude_auto_reply(message):
        if not message.text:
            return
        
        data_conv = load_conversations()
        if message.from_user.id not in data_conv.get("auto_reply", []):
            return

        if any(message.text.startswith(p) for p in command_prefixes_list):
            return

        is_private = message.chat.type == "private"
        is_reply_to_bot = False
        if message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id:
            is_reply_to_bot = True

        if is_private or (not is_private and is_reply_to_bot):
            chat_id_str = str(message.chat.id)
            chatid_uuid = data_conv["conversations"].get(chat_id_str)

            try:
                api_url = "https://claude.bbinl.site/api/claude"
                payload = {"q": message.text}
                if chatid_uuid:
                    payload["chatid"] = chatid_uuid

                response = await asyncio.to_thread(requests.post, api_url, json=payload, timeout=60)
                if response.status_code == 200:
                    res_data = response.json()
                    if res_data.get('response'):
                        reply_text = res_data['response']
                        new_chatid = res_data.get('chatid')

                        if chat_id_str in data_conv["conversations"]:
                            data_conv["conversations"][chat_id_str] = new_chatid
                            save_conversations(data_conv)

                        user = message.from_user
                        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                        await bot.reply_to(message, f"🤖 <b>𝗖𝗹𝗮𝘂𝗱𝗲 𝗔𝗜:</b>\n•──────────────────────•\n{reply_text}\n{footer}", parse_mode="HTML")
            except:
                pass
