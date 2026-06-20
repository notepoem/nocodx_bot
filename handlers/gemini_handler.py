import os
import re
import json
import html
import uuid
import asyncio
import requests

CONVERSATIONS_FILE = "cache/gemini_conversations.json"

ENDPOINT = "https://api.deepai.org/hacking_is_a_serious_crime"
MODEL    = "gemini-2.5-flash-lite"
MAX_HISTORY = 30

HEADERS = {
    "accept": "*/*",
    "api-key": "tryit-59261025865-77bc111e842889f15644d04cdb1136ad",
    "origin": "https://deepai.org",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


def load_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"sessions": {}, "uuids": {}, "auto_reply": [], "hints_shown": []}


def save_conversations(data):
    os.makedirs(os.path.dirname(CONVERSATIONS_FILE), exist_ok=True)
    try:
        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


def get_history(data_conv, chat_id_str):
    return data_conv.get("sessions", {}).get(chat_id_str, [])


def get_session_uuid(data_conv, chat_id_str):
    if "uuids" not in data_conv:
        data_conv["uuids"] = {}
    if chat_id_str not in data_conv["uuids"]:
        data_conv["uuids"][chat_id_str] = str(uuid.uuid4())
    return data_conv["uuids"][chat_id_str]


def append_history(data_conv, chat_id_str, role, content):
    if "sessions" not in data_conv:
        data_conv["sessions"] = {}
    if chat_id_str not in data_conv["sessions"]:
        data_conv["sessions"][chat_id_str] = []
    history = data_conv["sessions"][chat_id_str]
    if not isinstance(history, list):
        history = []
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    data_conv["sessions"][chat_id_str] = history
    return data_conv


def clear_history(data_conv, chat_id_str):
    if "sessions" in data_conv:
        data_conv["sessions"][chat_id_str] = []
    if "uuids" in data_conv:
        data_conv["uuids"][chat_id_str] = str(uuid.uuid4())
    return data_conv


def format_gemini_response(text):
    if not text:
        return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'^\* (.*)', r'• \1', text, flags=re.MULTILINE)

    def escape_code(match):
        code = match.group(1)
        return f'<pre><code>{html.escape(code)}</code></pre>'

    text = re.sub(r'```([\s\S]*?)```', escape_code, text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = text.replace('<br>', '\n')
    return text


def call_deepai(user_input, history, session_uuid):
    data = {
        "chat_style": "chat",
        "chatHistory": json.dumps(history),
        "model": MODEL,
        "session_uuid": session_uuid,
        "sensitivity_request_id": str(uuid.uuid4()),
        "hacker_is_stinky": "very_stinky",
        "enabled_tools": json.dumps(["image_generator", "image_editor"]),
    }

    response = requests.post(
        ENDPOINT,
        headers=HEADERS,
        data=data,
        stream=True,
        timeout=60,
    )

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}")

    full_response = ""
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            full_response += chunk.decode("utf-8")

    return full_response.strip()


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit):

    @custom_command_handler("gemini", "gem")
    async def handle_gemini(message):
        if check_usage_limit and not await check_usage_limit(message, "Gemini"):
            return

        parts_split = message.text.strip().split()
        command_part = parts_split[0]
        user_input = " ".join(parts_split[1:]).strip() if len(parts_split) > 1 else ""

        if not user_input:
            await bot.reply_to(
                message,
                f"❓ <b>Usage:</b> <code>{command_part} [your question]</code>\n"
                f"Example: <code>{command_part} How to learn Python?</code>",
                parse_mode="HTML"
            )
            return

        thinking = await bot.reply_to(message, "🤖 <b>Gemini is thinking...</b>", parse_mode="HTML")
        data_conv = load_conversations()
        chat_id_str = str(message.chat.id)
        history = get_history(data_conv, chat_id_str)
        session_uuid = get_session_uuid(data_conv, chat_id_str)

        try:
            history_with_current = history + [{"role": "user", "content": user_input}]
            reply_raw = await asyncio.to_thread(call_deepai, user_input, history_with_current, session_uuid)

            if not reply_raw:
                await bot.edit_message_text(
                    "❌ <b>Failed to get response from Gemini AI.</b>",
                    message.chat.id, thinking.message_id, parse_mode="HTML"
                )
                return

            reply_text = format_gemini_response(reply_raw)

            data_conv = append_history(data_conv, chat_id_str, "user", user_input)
            data_conv = append_history(data_conv, chat_id_str, "assistant", reply_raw)

            hint = ""
            if message.chat.type == "private" and message.from_user.id not in data_conv.get("hints_shown", []):
                hint = "\n\n💡 <b>Tip:</b> Use /ongem to enable auto-reply mode, /offgem to disable, /resetgem to clear history."
                if "hints_shown" not in data_conv:
                    data_conv["hints_shown"] = []
                data_conv["hints_shown"].append(message.from_user.id)

            save_conversations(data_conv)

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=thinking.message_id,
                text=f"🤖 <b>𝗚𝗲𝗺𝗶𝗻𝗶 𝗔𝗜:</b>\n•──────────────────────•\n{reply_text}{hint}\n{footer}",
                parse_mode="HTML"
            )

        except Exception as e:
            await bot.edit_message_text(
                f"❌ <b>Error:</b> {html.escape(str(e))}",
                message.chat.id, thinking.message_id, parse_mode="HTML"
            )

    @custom_command_handler("ongem")
    async def handle_on_gem(message):
        data_conv = load_conversations()
        user_id = message.from_user.id
        if user_id not in data_conv.get("auto_reply", []):
            if "auto_reply" not in data_conv:
                data_conv["auto_reply"] = []
            data_conv["auto_reply"].append(user_id)
            save_conversations(data_conv)
            await bot.reply_to(message, "🔔 Gemini Auto-reply turned <b>ON</b>\n\nI will respond to your messages automatically!", parse_mode="HTML")
        else:
            await bot.reply_to(message, "ℹ️ Gemini Auto-reply is already <b>ON</b>", parse_mode="HTML")

    @custom_command_handler("offgem")
    async def handle_off_gem(message):
        data_conv = load_conversations()
        user_id = message.from_user.id
        if "auto_reply" in data_conv and user_id in data_conv["auto_reply"]:
            data_conv["auto_reply"].remove(user_id)
            save_conversations(data_conv)
            await bot.reply_to(message, "🔕 Gemini Auto-reply turned <b>OFF</b>", parse_mode="HTML")
        else:
            await bot.reply_to(message, "ℹ️ Gemini Auto-reply is already <b>OFF</b>", parse_mode="HTML")

    @custom_command_handler("resetgem")
    async def handle_reset_gem(message):
        data_conv = load_conversations()
        chat_id_str = str(message.chat.id)
        data_conv = clear_history(data_conv, chat_id_str)
        save_conversations(data_conv)
        await bot.reply_to(message, "🔄 Gemini conversation history <b>cleared!</b>", parse_mode="HTML")

    @bot.message_handler(func=lambda message: message.text and not any(message.text.startswith(p) for p in command_prefixes_list) and message.from_user.id in load_conversations().get("auto_reply", []))
    async def handle_gemini_auto_reply(message):
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

        if not (is_private or (not is_private and is_reply_to_bot)):
            return

        chat_id_str = str(message.chat.id)
        history = get_history(data_conv, chat_id_str)
        session_uuid = get_session_uuid(data_conv, chat_id_str)

        thinking = await bot.reply_to(message, "🤖 <b>Gemini is thinking...</b>", parse_mode="HTML")
        try:
            history_with_current = history + [{"role": "user", "content": message.text}]
            reply_raw = await asyncio.to_thread(call_deepai, message.text, history_with_current, session_uuid)

            if not reply_raw:
                await bot.edit_message_text(
                    "❌ <b>No response from Gemini.</b>",
                    message.chat.id, thinking.message_id, parse_mode="HTML"
                )
                return

            reply_text = format_gemini_response(reply_raw)

            data_conv = append_history(data_conv, chat_id_str, "user", message.text)
            data_conv = append_history(data_conv, chat_id_str, "assistant", reply_raw)
            save_conversations(data_conv)

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            await bot.edit_message_text(
                f"🤖 <b>𝗚𝗲𝗺𝗶𝗻𝗶 𝗔𝗜:</b>\n•──────────────────────•\n{reply_text}\n{footer}",
                message.chat.id, thinking.message_id, parse_mode="HTML"
            )

        except Exception as e:
            await bot.edit_message_text(
                f"❌ <b>Error:</b> {html.escape(str(e))}",
                message.chat.id, thinking.message_id, parse_mode="HTML"
            )
