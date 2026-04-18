import requests
from telebot import types
import asyncio

API_URL_SEND_CODE = "https://session-string.bbinl.site/api/send_code"
API_URL_LOGIN = "https://session-string.bbinl.site/api/login"

# user_data[user_id] = {
#   'state': 'waiting_api_id'|'waiting_api_hash'|'waiting_phone'|'waiting_otp',
#   'library': str, 'api_id': str, 'api_hash': str,
#   'phone': str, 'phone_code_hash': str, 'session_id': str
# }

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    user_data = {}

    async def send_code_request(api_id, api_hash, phone, library):
        payload = {"api_id": api_id, "api_hash": api_hash, "phone": phone, "library": library}
        try:
            response = await asyncio.to_thread(requests.post, API_URL_SEND_CODE, json=payload, timeout=15)
            return (True, response.json()) if response.status_code == 200 else (False, response.text)
        except Exception as e:
            return False, str(e)

    async def login_request(payload):
        try:
            response = await asyncio.to_thread(requests.post, API_URL_LOGIN, json=payload, timeout=15)
            return (True, response.json()) if response.status_code == 200 else (False, response.text)
        except Exception as e:
            return False, str(e)

    async def do_send_code_and_wait_otp(message, user_id):
        chat_id = message.chat.id
        lib = user_data[user_id].get('library', 'pyrogram')
        phone = user_data[user_id]['phone']
        status_msg = await bot.send_message(chat_id, "🔄 Sending code...")
        success, resp = await send_code_request(
            user_data[user_id]['api_id'], user_data[user_id]['api_hash'], phone, lib
        )
        if success and "phone_code_hash" in resp and "session_id" in resp:
            user_data[user_id]['phone_code_hash'] = resp['phone_code_hash']
            user_data[user_id]['session_id'] = resp['session_id']
            user_data[user_id]['state'] = 'waiting_otp'
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_message(
                chat_id,
                "📩 <b>Code sent!</b>\n\nPlease enter the OTP you received.\n\n"
                "<i>If it's like 12345, send it as <code>1 2 3 4 5</code> to avoid Telegram link preview.</i>",
                parse_mode="HTML"
            )
        else:
            await bot.edit_message_text(
                f"❌ Failed to send code: {resp}",
                chat_id=chat_id, message_id=status_msg.message_id
            )
            user_data.pop(user_id, None)

    async def do_login_bot_token(chat_id, user_id, bot_token):
        lib = user_data[user_id].get('library', 'pyrogram')
        payload = {
            "api_id": user_data[user_id]['api_id'],
            "api_hash": user_data[user_id]['api_hash'],
            "bot_token": bot_token,
            "library": lib
        }
        status_msg = await bot.send_message(chat_id, "🔄 Logging in with Bot Token...")
        success, resp = await login_request(payload)
        if success and "session_string" in resp:
            await bot.delete_message(chat_id, status_msg.message_id)
            await bot.send_message(chat_id, f"✅ <b>{lib.title()} Session Generated!</b>", parse_mode="HTML")
            await bot.send_message(chat_id, f"<code>{resp['session_string']}</code>", parse_mode="HTML")
        else:
            await bot.edit_message_text(f"❌ Login Failed: {resp}", chat_id=chat_id, message_id=status_msg.message_id)
        user_data.pop(user_id, None)

    # ── /string command ────────────────────────────────────────────────────────

    @custom_command_handler("string", "session")
    async def start_session_gen(message):
        if check_usage_limit and not await check_usage_limit(message, "SessionString"):
            return
        user_id = message.from_user.id
        user_data[user_id] = {}
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Pyrogram", callback_data="ss_library_pyrogram"),
            types.InlineKeyboardButton("Telethon", callback_data="ss_library_telethon")
        )
        await bot.send_message(
            message.chat.id,
            "📜 <b>Choose the library for session generation:</b>",
            reply_markup=markup, parse_mode="HTML"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('ss_library_'))
    async def callback_library_selection(call):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        library = call.data.replace("ss_library_", "")
        if library not in ("pyrogram", "telethon"):
            return
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['library'] = library
        user_data[user_id]['state'] = 'waiting_api_id'
        await bot.delete_message(chat_id, call.message.message_id)
        await bot.send_message(
            chat_id,
            f"✅ Selected: <b>{library.title()}</b>\n\n🆔 <b>Please enter your API ID:</b>\n\n"
            "(You can get it from my.telegram.org)",
            parse_mode="HTML"
        )

    # ── State machine message handler ──────────────────────────────────────────

    @bot.message_handler(func=lambda m: (
        m.from_user.id in user_data and
        user_data[m.from_user.id].get('state') in
        ('waiting_api_id', 'waiting_api_hash', 'waiting_phone', 'waiting_otp') and
        not (m.text or "").startswith('/')
    ))
    async def session_step_handler(message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        state = user_data[user_id].get('state')

        if message.content_type != 'text':
            await bot.send_message(chat_id, "❌ Please send text only. Start over with /string")
            user_data.pop(user_id, None)
            return

        text = message.text.strip()

        if state == 'waiting_api_id':
            if not text.isdigit():
                await bot.send_message(chat_id, "⚠️ API ID must be a number. Please enter it again:")
                return
            user_data[user_id]['api_id'] = text
            user_data[user_id]['state'] = 'waiting_api_hash'
            await bot.send_message(chat_id, "🔑 <b>Now enter your API HASH:</b>", parse_mode="HTML")

        elif state == 'waiting_api_hash':
            user_data[user_id]['api_hash'] = text
            user_data[user_id]['state'] = 'waiting_phone'
            await bot.send_message(
                chat_id,
                "📞 <b>Enter phone number with country code (or Bot Token):</b>\n"
                "Example: <code>+8801xxxxxxxxx</code> or <code>123456:ABC...</code>",
                parse_mode="HTML"
            )

        elif state == 'waiting_phone':
            auth_key = text.replace(" ", "")
            if ':' in auth_key and not auth_key.startswith('+'):
                await do_login_bot_token(chat_id, user_id, auth_key)
            else:
                user_data[user_id]['phone'] = auth_key
                await do_send_code_and_wait_otp(message, user_id)

        elif state == 'waiting_otp':
            otp = text.replace(" ", "").replace("-", "")
            status_msg = await bot.send_message(chat_id, "🔄 Verifying code & logging in...")
            payload = {
                "api_id": user_data[user_id]['api_id'],
                "api_hash": user_data[user_id]['api_hash'],
                "phone": user_data[user_id]['phone'],
                "phone_code": otp,
                "phone_code_hash": user_data[user_id]['phone_code_hash'],
                "session_id": user_data[user_id]['session_id'],
                "library": user_data[user_id].get('library', 'pyrogram')
            }
            success, resp = await login_request(payload)
            if success and "session_string" in resp:
                lib = user_data[user_id].get('library', 'pyrogram')
                await bot.delete_message(chat_id, status_msg.message_id)
                await bot.send_message(chat_id, f"✅ <b>{lib.title()} Session Generated!</b>", parse_mode="HTML")
                await bot.send_message(chat_id, f"<code>{resp['session_string']}</code>", parse_mode="HTML")
                await bot.send_message(chat_id, "⚠️ <i>Keep this string safe! It grants full access to your account.</i>", parse_mode="HTML")
            else:
                await bot.edit_message_text(f"❌ Login Failed: {resp}", chat_id=chat_id, message_id=status_msg.message_id)
            user_data.pop(user_id, None)

    # ── Argument-based commands (/pyrostring, /telestring) ─────────────────────

    async def handle_arg_command(message, library):
        try:
            text = message.text.split(maxsplit=1)[1]
        except IndexError:
            cmd = message.text.split()[0][1:]
            await bot.reply_to(
                message,
                f"❌ Usage: <code>/{cmd} api_id,api_hash,phone_or_token</code>\n\nExample:\n"
                f"<code>/{cmd} 123456,abcdef123456,+1234567890</code>",
                parse_mode="HTML"
            )
            return

        parts = [p.strip() for p in text.split(',')]
        if len(parts) != 3:
            await bot.reply_to(message, "❌ Invalid format! Please use: <code>api_id,api_hash,phone_or_token</code>", parse_mode="HTML")
            return

        api_id, api_hash, auth_key = parts
        chat_id = message.chat.id
        user_id = message.from_user.id

        user_data[user_id] = {'api_id': api_id, 'api_hash': api_hash, 'library': library}

        if ':' in auth_key and not auth_key.startswith('+'):
            await do_login_bot_token(chat_id, user_id, auth_key)
        else:
            user_data[user_id]['phone'] = auth_key
            await do_send_code_and_wait_otp(message, user_id)

    @custom_command_handler("pyrostring")
    async def pyrostring_handler(message):
        await handle_arg_command(message, "pyrogram")

    @custom_command_handler("telestring")
    async def telestring_handler(message):
        await handle_arg_command(message, "telethon")
