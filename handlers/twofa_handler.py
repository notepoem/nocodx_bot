import time
import threading
import urllib.parse
import cv2
import numpy as np
import pyotp
import html
from telebot import types
import asyncio

DEFAULT_INTERVAL = 30
AUTO_UPDATE_DURATION = 120  
active_updates = {}
updates_lock = threading.Lock()

def get_totp_code(secret):
    try:
        clean_secret = secret.replace(" ", "").upper()
        totp = pyotp.TOTP(clean_secret, interval=DEFAULT_INTERVAL)
        current_time = int(time.time())
        remaining = DEFAULT_INTERVAL - (current_time % DEFAULT_INTERVAL)
        return totp.now(), remaining
    except Exception:
        return None, None

def generate_progress_bar(remaining_time):
    total_blocks = 10
    filled_blocks = int((remaining_time / DEFAULT_INTERVAL) * total_blocks)
    return "🟩" * filled_blocks + "⬜" * (total_blocks - filled_blocks)

def create_keyboard(secret, code, unique_id="0_0"):
    markup = types.InlineKeyboardMarkup()
    cb_data = f"2fa_reg_{unique_id}" 
    re_gen_btn = types.InlineKeyboardButton("♻️ Refresh", callback_data=cb_data)
    copy_btn = types.InlineKeyboardButton("📋 Copy Code", callback_data=f"2fa_cp_{code}")
    markup.add(re_gen_btn, copy_btn)
    return markup

def format_response(secret, code, remaining, footer=""):
    progress_bar = generate_progress_bar(remaining)
    return (
        f"🔐 <b>𝟮𝗙𝗔 𝗔𝘂𝘁𝗵𝗲𝗻𝘁𝗶𝗰𝗮𝘁𝗶𝗼𝗻</b>\n\n"
        f"🔢 <b>𝗖𝗼𝗱𝗲:</b> <code>{code}</code>\n"
        f"🔑 <b>𝗞𝗲𝘆:</b> <code>{secret}</code>\n\n"
        f"⏳ <b>𝗘𝘅𝗽𝗶𝗿𝗲𝘀 𝗶𝗻 {remaining}𝘀:</b>\n"
        f"{progress_bar}\n"
        f"\n{footer}"
    )

def register(bot, custom_command_handler, COMMAND_PREFIXES, check_usage_limit=None):

    async def auto_update_worker():
        while True:
            await asyncio.sleep(3)
            to_remove = []
            with updates_lock:
                for (chat_id, msg_id), (secret, start_time, footer) in list(active_updates.items()):
                    if time.time() - start_time > AUTO_UPDATE_DURATION:
                        to_remove.append((chat_id, msg_id))
                        continue

                    code, remaining = get_totp_code(secret)
                    try:
                        unique_id = f"{chat_id}_{msg_id}"
                        await bot.edit_message_text(
                            format_response(secret, code, remaining, footer),
                            chat_id, msg_id,
                            parse_mode="HTML",
                            reply_markup=create_keyboard(secret, code, unique_id)
                        )
                    except Exception as e:
                        if "message is not modified" not in str(e):
                            to_remove.append((chat_id, msg_id))

                for key in to_remove:
                    active_updates.pop(key, None)

    def _run_worker():
        asyncio.run(auto_update_worker())
    threading.Thread(target=_run_worker, daemon=True).start()

    @custom_command_handler("2fa")
    async def handle_2fa(message):
        if check_usage_limit and not await check_usage_limit(message, "2FA Authenticator"):
            return
        secret = ""

        if message.reply_to_message and message.reply_to_message.photo:
            photo = message.reply_to_message.photo[-1]
            secret = await scan_qr(bot, photo.file_id)

        elif message.photo:
            photo = message.photo[-1]
            secret = await scan_qr(bot, photo.file_id)

        else:
            text_parts = message.text.split(None, 1)
            if len(text_parts) > 1:
                secret = text_parts[1].strip()

        if not secret:
            await bot.reply_to(message, "❌ <b>No Secret key or QR code Found!</b>\nUse: <code>/2fa secret_key</code> or send qr and give the /2fa command in reply", parse_mode="HTML")
            return

        await process_2fa(bot, message, secret)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("2fa_"))
    async def handle_callback(call):
        if "reg_" in call.data:
            unique_id_str = call.data.replace("2fa_reg_", "")

            try:
                chat_id_str, msg_id_str = unique_id_str.split("_")
                key = (int(chat_id_str), int(msg_id_str))
                
                with updates_lock:
                    data = active_updates.get(key)
                
                if data:
                    secret = data[0]
                    await process_2fa(bot, call.message, secret, edit=True) 
                    await bot.answer_callback_query(call.id, "Refreshed! ✅")
                else:
                    await bot.answer_callback_query(call.id, "Session expired. Please send command again.", show_alert=True)
            except Exception:
                 await bot.answer_callback_query(call.id, "Error refreshing.", show_alert=True)
        elif "cp_" in call.data:
            code = call.data.replace("2fa_cp_", "")
            await bot.answer_callback_query(call.id, f"Code {code} copied (manually)!", show_alert=False)

async def scan_qr(bot, file_id):
    try:
        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        nparr = np.frombuffer(downloaded_file, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(image)

        if data:
            if data.startswith("otpauth://"):
                parsed = urllib.parse.urlparse(data)
                params = urllib.parse.parse_qs(parsed.query)
                return params.get('secret', [None])[0]
            return data
    except:
        pass
    return None

async def process_2fa(bot, message, secret, edit=False):
    code, remaining = get_totp_code(secret)
    if not code:
        await bot.reply_to(message, "❌ <b>Wrong Secret Key!</b>", parse_mode="HTML")
        return

    user = message.from_user
    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
    footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

    text = format_response(secret, code, remaining, footer)
    markup = create_keyboard(secret, code)

    if edit:
        sent_msg = await bot.edit_message_text(text, message.chat.id, message.message_id, parse_mode="HTML", reply_markup=markup)
    else:
        sent_msg = await bot.reply_to(message, text, parse_mode="HTML", reply_markup=markup)
    
    unique_id = f"{message.chat.id}_{sent_msg.message_id}"
    markup = create_keyboard(secret, code, unique_id)
    await bot.edit_message_reply_markup(message.chat.id, sent_msg.message_id, reply_markup=markup)

    with updates_lock:
        active_updates[(message.chat.id, sent_msg.message_id)] = (secret, time.time(), footer)