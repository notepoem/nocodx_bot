import requests
import json
import os
import asyncio

CONVERSATIONS_FILE = "cache/pplx_conversations.json"

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
        
    @custom_command_handler("perplexity", "pplx")
    async def handle_perplexity(message):
        if check_usage_limit and not await check_usage_limit(message, "Perplexity"):
            return
        
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             user_input = " ".join(parts_split[1:]).strip()
        else:
             user_input = ""

        if not user_input:
            await bot.reply_to(
                message, 
                f"❓ Usage: `{command_prefixes_list[0]}perplexity [prompt]`\n"
                f"Example: `{command_prefixes_list[0]}perplexity What is AI?`", 
                parse_mode="Markdown"
            )
            return

        thinking_message = await bot.reply_to(message, "🔍 Searching with Perplexity AI...")

        data_conv = load_conversations()
        chat_id_str = str(message.chat.id)
        session = data_conv["conversations"].get(chat_id_str)

        try:
            api_url = "https://pplx-api.vercel.app/api/ask"
            payload = {
                "prompt": user_input,
                "mode": "concise",
                "search_focus": "internet",
                "model": "turbo"
            }
            if session and isinstance(session, dict):
                if session.get("chatid"):
                    payload["chatid"] = session['chatid']
                if session.get("token"):
                    payload["token"] = session['token']
            
            response = await asyncio.to_thread(requests.post, api_url, json=payload, timeout=60)
            response.raise_for_status()
            res_data = response.json()
            
            # Use html_answer if available, otherwise fallback to answer
            reply_text = res_data.get('html_answer') or res_data.get('answer')
            
            if reply_text:
                metadata = res_data.get('metadata', {})
                new_chatid = metadata.get('chatid')
                new_token = metadata.get('token')
                
                if chat_id_str in data_conv["conversations"]:
                    data_conv["conversations"][chat_id_str] = {
                        "chatid": new_chatid,
                        "token": new_token
                    }
                    save_conversations(data_conv)

                # Sources
                sources_text = ""
                if res_data.get('sources'):
                    sources_text = "\n\n📚 <b>𝗦𝗼𝘂𝗿𝗰𝗲𝘀:</b>\n"
                    for idx, src in enumerate(res_data['sources'][:3], 1):
                        sources_text += f"{idx}. <a href='{src['url']}'>{src['name']}</a>\n"

                hint = ""
                if message.chat.type == "private" and message.from_user.id not in data_conv["hints_shown"]:
                    hint = f"\n\n💡 <b>Tip:</b> Use /onpplx to enable conversational mode and /offpplx to reset context."
                    data_conv["hints_shown"].append(message.from_user.id)
                    save_conversations(data_conv)

                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                full_reply = f"🤖 <b>𝗣𝗲𝗿𝗽𝗹𝗲𝘅𝗶𝘁𝘆 𝗔𝗜:</b>\n•──────────────────────•\n{reply_text}{sources_text}{hint}\n{footer}"
                
                if len(full_reply) > 4096:
                    full_reply = full_reply[:4093] + "..."

                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text=full_reply,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            else:
                await bot.edit_message_text(
                    chat_id=thinking_message.chat.id,
                    message_id=thinking_message.message_id,
                    text="❌ Failed to get response from Perplexity AI."
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

    @custom_command_handler("onpplx")
    async def handle_on_pplx(message):
        data_conv = load_conversations()
        chat_id_str = str(message.chat.id)
        user_id = message.from_user.id
        
        changed = False
        if chat_id_str not in data_conv["conversations"]:
            data_conv["conversations"][chat_id_str] = {} # Persistent convo
            changed = True
            
        if user_id not in data_conv.get("auto_reply", []):
            if "auto_reply" not in data_conv: data_conv["auto_reply"] = []
            data_conv["auto_reply"].append(user_id)
            changed = True
            
        if changed:
            save_conversations(data_conv)
            await bot.reply_to(message, "✅ Perplexity Conversational & Auto-reply mode turned <b>ON</b>", parse_mode="HTML")
        else:
            await bot.reply_to(message, "ℹ️ Perplexity Conversational & Auto-reply mode is already <b>ON</b>", parse_mode="HTML")

    @custom_command_handler("offpplx")
    async def handle_off_pplx(message):
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
            await bot.reply_to(message, "⭕ Perplexity Conversational & Auto-reply turned <b>OFF</b>", parse_mode="HTML")
        else:
            await bot.reply_to(message, "ℹ️ Perplexity Conversational & Auto-reply is already <b>OFF</b>", parse_mode="HTML")

    @bot.message_handler(func=lambda message: message.text and not any(message.text.startswith(p) for p in command_prefixes_list) and message.from_user.id in load_conversations().get("auto_reply", []))
    async def handle_pplx_auto_reply(message):
        if not message.text:
            return
        
        data_conv = load_conversations()
        
        is_private = message.chat.type == "private"
        is_reply_to_bot = False
        if message.reply_to_message and message.reply_to_message.from_user.id == (await bot.get_me()).id:
            is_reply_to_bot = True

        if is_private or (not is_private and is_reply_to_bot):
            chat_id_str = str(message.chat.id)
            session = data_conv["conversations"].get(chat_id_str)

            try:
                api_url = "https://pplx-api.vercel.app/api/ask"
                payload = {
                    "prompt": message.text,
                    "mode": "concise",
                    "search_focus": "internet",
                    "model": "turbo"
                }
                if session and isinstance(session, dict):
                    if session.get("chatid"): payload["chatid"] = session['chatid']
                    if session.get("token"): payload["token"] = session['token']

                response = await asyncio.to_thread(requests.post, api_url, json=payload, timeout=60)
                if response.status_code == 200:
                    res_data = response.json()
                    reply_text = res_data.get('html_answer') or res_data.get('answer')
                    
                    if reply_text:
                        metadata = res_data.get('metadata', {})
                        if chat_id_str in data_conv["conversations"]:
                            data_conv["conversations"][chat_id_str] = {
                                "chatid": metadata.get('chatid'),
                                "token": metadata.get('token')
                            }
                            save_conversations(data_conv)

                        user = message.from_user
                        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                        await bot.reply_to(message, f"🤖 <b>𝗣𝗲𝗿𝗽𝗹𝗲𝘅𝗶𝘁𝘆 𝗔𝗜:</b>\n•──────────────────────•\n{reply_text}\n{footer}", parse_mode="HTML", disable_web_page_preview=True)
            except:
                pass
