import os
import re
import string
import asyncio
import telebot
import cleanup
import system_manager

import uvicorn
from fastapi import FastAPI
from threading import Thread
from telebot import apihelper
from telebot.async_telebot import AsyncTeleBot, BaseMiddleware
from cleanup import cache_manager

from broadcast.user_database import UserDatabase
from broadcast.sticker_manager import StickerPackManager
from broadcast.sheets_manager import GoogleSheetsSync, SHEET_ID, SERVICE_ACCOUNT_JSON
import broadcast.lang_manager as lang_manager

apihelper.ENABLE_MIDDLEWARE = True
cleanup.cleanup_project()

# Handlers import
from handlers import (
    admin_handler, b3_handler, bgremove_handler, bin_handler,
    bomb_handler, broadcast_handler, chk_handler, cpf_handler,
    claude_handler, deepseek_handler, download_handler, enh_handler,
    exchange_handler, fakeAddress_handler, faceswap_handler, gen_handler,
    gemini_handler, github_handler, gpt_handler, grok_handler,
    iban_handler, imagine_handler, meta_handler,
    movie_handler, perplexity_handler, pfp_handler, qr_handler,
    qwen_handler, reveal_handler, say_handler, scribd_handler,
    shopify_handler, site_handler, spam_handler, start_handler,
    stripe_handler, routing_handler, terabox_handler,
    story_handler, translate_handler, truecaller_handler, twofa_handler,
    userinfo_handler, upload_handler, conv_handler, wth_handler, yt_handler,
    freepik_handler,
    spotify_handler, share_handler, sticker_handler, proxy_handler, base64_handler,
    string_session_handler, yt_metadata_handler, ocr_handler, prompt_handler, websrc_handler,
    mail_handler, tgauth_handler, cgmail_handler, vbv_handler, vrm_handler,
    number_handler
)

from config import BOT_TOKEN
bot = AsyncTeleBot(BOT_TOKEN, parse_mode="HTML")

# ── URL sanitizer: strip API URLs from all outgoing bot messages ──────────────
_URL_RE = re.compile(r'https?://(?!t\.me/|files\.catbox\.moe/|litter\.catbox\.moe/|0x0\.st/)[^\s<>"]+|www\.[^\s<>"]+', re.IGNORECASE)

def _sanitize(text):
    if not isinstance(text, str):
        return text
    def _replace(m):
        start = m.start()
        url = m.group(0)
        # Don't hide URLs that are the value of an HTML attribute (href=, src=, url=)
        preceding = text[max(0, start - 6):start]
        if any(attr in preceding for attr in ('href=', 'src="', "src='", 'url=')):
            return url
        # Don't hide URLs that are the visible text of an <a href="URL">URL</a> tag
        search_window = text[max(0, start - len(url) - 60):start]
        if f'href="{url}"' in search_window or f"href='{url}'" in search_window:
            return url
        return '[hidden]'
    return _URL_RE.sub(_replace, text)

_orig_reply_to          = bot.reply_to
_orig_send_message      = bot.send_message
_orig_edit_message_text = bot.edit_message_text
_orig_answer_cb_query   = bot.answer_callback_query

async def _safe_reply_to(message, text, *args, **kw):
    return await _orig_reply_to(message, _sanitize(text), *args, **kw)

async def _safe_send_message(chat_id, text, *args, **kw):
    return await _orig_send_message(chat_id, _sanitize(text), *args, **kw)

async def _safe_edit_message_text(text, *args, **kw):
    return await _orig_edit_message_text(_sanitize(text), *args, **kw)

async def _safe_answer_cb_query(callback_query_id, text=None, *args, **kw):
    return await _orig_answer_cb_query(callback_query_id, _sanitize(text) if text else text, *args, **kw)

bot.reply_to              = _safe_reply_to
bot.send_message          = _safe_send_message
bot.edit_message_text     = _safe_edit_message_text
bot.answer_callback_query = _safe_answer_cb_query
# ─────────────────────────────────────────────────────────────────────────────

COMMAND_PREFIXES = list(string.punctuation)

print("\n" + "="*60)
print("🔄 STARTUP: Initializing system with Google Sheets sync")
print("="*60 + "\n")

gs_sync = None
try:
    print("📡 Connecting to Google Sheets...")
    gs_sync = GoogleSheetsSync(SHEET_ID, SERVICE_ACCOUNT_JSON)
    gs_sync.ensure_sheets_exist()
    print("✅ Google Sheets API connected\n")
    print("📥 Pulling data from Google Sheets...")
    import json as json_lib

    sheets_bot_users = gs_sync.pull_bot_users()
    if sheets_bot_users and sheets_bot_users.get("users"):
        print(f"✅ Pulled {len(sheets_bot_users['users'])} users from bot_users sheet")
        with open("broadcast/bot_users.json", "w", encoding='utf-8') as f:
            json_lib.dump(sheets_bot_users, f, ensure_ascii=False, indent=2)
    else:
        with open("broadcast/bot_users.json", "w", encoding='utf-8') as f:
            json_lib.dump({"users": {}}, f, ensure_ascii=False, indent=2)

    sheets_sticker_packs = gs_sync.pull_sticker_packs()
    if sheets_sticker_packs and sheets_sticker_packs.get("packs"):
        print(f"✅ Pulled sticker packs for {len(sheets_sticker_packs['packs'])} users")
        with open("broadcast/sticker_packs.json", "w", encoding='utf-8') as f:
            json_lib.dump(sheets_sticker_packs, f, ensure_ascii=False, indent=2)
    else:
        print("⚠️ No sticker_packs in Sheets")
        with open("broadcast/sticker_packs.json", "w", encoding='utf-8') as f:
            json_lib.dump({"packs": {}}, f, ensure_ascii=False, indent=2)

    print("✅ Data synced from Google Sheets\n")

except Exception as e:
    print(f"⚠️ Google Sheets error: {e}")
    print("⚠️ Creating empty local databases\n")
    import json as json_lib
    with open("broadcast/bot_users.json", "w", encoding='utf-8') as f:
        json_lib.dump({"users": {}}, f, ensure_ascii=False, indent=2)
    with open("broadcast/sticker_packs.json", "w", encoding='utf-8') as f:
        json_lib.dump({"packs": {}}, f, ensure_ascii=False, indent=2)
    gs_sync = None

print("💾 Initializing local databases...")
user_db = UserDatabase(db_path="broadcast/bot_users.json")
sticker_manager = StickerPackManager("broadcast/sticker_packs.json")
lang_manager.init(user_db)
print("✅ Databases initialized\n")

print("="*60)
print("✨ System ready - local data is source of truth")
print("="*60 + "\n")

def sync_to_sheets_async():
    if gs_sync:
        try:
            bot_users_data = {"users": user_db._load_data_unsafe().get("users", {})}
            stickers_data = sticker_manager.get_all_data()
            gs_sync.sync_all_data_async(bot_users_data, stickers_data)
        except Exception as e:
            print(f"⚠️ Error preparing background sync: {e}")

class SaveUserMiddleware(BaseMiddleware):
    def __init__(self):
        self.update_types = ['message']

    async def pre_process(self, message, data):
        try:
            user = message.from_user
            user_db.add_or_update_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
        except Exception as e:
            print(f"Error saving user: {e}")

    async def post_process(self, message, data, exception):
        pass

bot.setup_middleware(SaveUserMiddleware())

def custom_command_handler(*command_names):
    def decorator(handler_func):
        @bot.message_handler(func=lambda message: message.text and any(
            message.text.split()[0].lower().split('@')[0] == f"{prefix}{command_name}"
            for command_name in command_names
            for prefix in COMMAND_PREFIXES
        ))
        async def wrapper(message):
            return await handler_func(message)
        return wrapper
    return decorator

app = FastAPI()

@app.get('/')
def home():
    return {"status": "Bot is running!"}

def run():
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='warning')

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

keep_alive()

async def check_usage_limit(message, handler_name):
    user_id = message.from_user.id
    user_data = user_db.get_user(user_id)

    if not user_data:
        return True

    if user_data.get('is_banned', False):
        await bot.reply_to(message, "🚫 You are BANNED from using this bot.")
        return False

    return True

def register_handler(handler_module, handler_name, pass_user_db=False):
    try:
        import inspect
        sig = inspect.signature(handler_module.register)
        params = sig.parameters

        args = [bot, custom_command_handler, COMMAND_PREFIXES]

        if pass_user_db or "user_db" in params:
            args.append(user_db)

        kwargs = {}
        if "check_usage_limit" in params:
            kwargs["check_usage_limit"] = check_usage_limit
        if "sticker_manager" in params:
            kwargs["sticker_manager"] = sticker_manager
        if "sync_func" in params:
            kwargs["sync_func"] = sync_to_sheets_async

        handler_module.register(*args, **kwargs)
        print(f"✅ {handler_name} handler loaded successfully")
    except Exception as e:
        print(f"❌ {handler_name} handler failed to load: {str(e)}")

print("\n🔄 Loading command handlers...")
print("-" * 40)

register_handler(admin_handler, "Admin", pass_user_db=True)
register_handler(b3_handler, "B3")
register_handler(bgremove_handler, "BG Remove")
register_handler(bin_handler, "Bin")
register_handler(bomb_handler, "Bomb")
register_handler(broadcast_handler, "Broadcast", pass_user_db=True)
register_handler(chk_handler, "Chk")
register_handler(cpf_handler, "CPF")
register_handler(claude_handler, "Claude")
register_handler(deepseek_handler, "Deepseek")
register_handler(download_handler, "Download")
register_handler(enh_handler, "enh")
register_handler(exchange_handler, "Exchange")
register_handler(fakeAddress_handler, "Fake Address")
register_handler(faceswap_handler, "Face Swap")
register_handler(gen_handler, "Gen")
register_handler(gemini_handler, "Gemini")
register_handler(github_handler, "Github")
register_handler(gpt_handler, "GPT")
register_handler(grok_handler, "Grok")
register_handler(iban_handler, "Iban")
register_handler(imagine_handler, "Imagine")
register_handler(meta_handler, "Meta")
register_handler(movie_handler, "movie")
register_handler(perplexity_handler, "Perplexity")
register_handler(pfp_handler, "Pfp")
register_handler(qr_handler, "Qr")
register_handler(qwen_handler, "Qwen")
register_handler(reveal_handler, "Reveal")
register_handler(say_handler, "Say")
register_handler(shopify_handler, "Shopify")
register_handler(scribd_handler, "Scribd")
register_handler(site_handler, "Site")
register_handler(spam_handler, "Spam")
register_handler(start_handler, "Start")
register_handler(stripe_handler, "Stripe")
register_handler(routing_handler, "Routing")
register_handler(terabox_handler, "Terabox")
register_handler(story_handler, "Story")
register_handler(freepik_handler, "Freepik")
register_handler(translate_handler, "Translate")
register_handler(truecaller_handler, "Truecaller")
register_handler(twofa_handler, "2FA Authenticator")
register_handler(userinfo_handler, "Userinfo")
register_handler(upload_handler, "Upload")
register_handler(conv_handler, "File Converter")
register_handler(wth_handler, "weather")
register_handler(yt_handler, "yt")
register_handler(spotify_handler, "Spotify")
register_handler(share_handler, "Share")
register_handler(sticker_handler, "Sticker")
register_handler(proxy_handler, "Proxy")
register_handler(base64_handler, "Base64")
register_handler(string_session_handler, "SessionString")
register_handler(yt_metadata_handler, "YouTubeInfo")
register_handler(ocr_handler, "OCR")
register_handler(prompt_handler, "Prompt")
register_handler(websrc_handler, "Web Scraper")
register_handler(mail_handler, "Mail")
register_handler(tgauth_handler, "TG Auth")
register_handler(cgmail_handler, "Mail Check")
register_handler(vbv_handler, "VBV")
register_handler(vrm_handler, "Vocal Remover")
register_handler(number_handler, "Temp Number")

print("-" * 40)
print("✨ Handler registration completed!\n")

cache_manager.start_cleanup_task()

if __name__ == '__main__':
    print("🤖 Bot is running...")
    asyncio.run(bot.infinity_polling())
