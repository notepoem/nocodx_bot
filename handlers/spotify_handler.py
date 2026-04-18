import os
import requests
import re
import time
from telebot import TeleBot
from telebot.types import (

    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
import asyncio

# === APIs ===
SEARCH_API = "https://spoti-dlx.vercel.app/api/search?query="
DL_SPOTMATE_API = "https://spoti-dlx.vercel.app/api/spotmate?url="
DL_SPOWLOAD_API = "https://spoti-dlx.vercel.app/api/spowload?url="

# === State ===
user_search_results = {}

# === API Functions ===
async def search_spotify(query):
    try:
        url = f"{SEARCH_API}{query}"
        response = await asyncio.to_thread(requests.get, url, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("results", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"Spotify Search Error: {e}")
        return []

async def download_file(url, filename):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        r = await asyncio.to_thread(requests.get, url, stream=True, timeout=120)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Download Error: {e}")
        if os.path.exists(filename):
            os.remove(filename)
        return False

def register(bot: TeleBot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    
    @custom_command_handler("sp")
    async def handle_spotify(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "Download"): 
            return

        text = message.text or ""
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2:
            await bot.reply_to(message, f"🎵 Spotify Downloader\n\nUsage:\n`{command_prefixes_list[0]}sp <song name>` (Search)\n`{command_prefixes_list[0]}sp <url>` (Direct Download)", parse_mode="Markdown")
            return

        query = parts[1].strip()
        
        if "open.spotify.com" in query:
             await process_direct_link(bot, message, query)
             return

        wait_msg = await bot.reply_to(message, "🔍 Searching Spotify...")
        results = await search_spotify(query)
        
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"
        
        if not results:
            await bot.edit_message_text("❌ No results found.", message.chat.id, wait_msg.message_id)
            return

        user_search_results[message.chat.id] = results[:10]
        
        text_lines = []
        for idx, item in enumerate(results[:10]):
            title = item.get("title", "Unknown")
            artist = item.get("artist", "Unknown")
            duration = item.get("duration", 0)
            
            try:
                mins = int(float(duration) // 60)
                secs = int(float(duration) % 60)
                dur_str = f"{mins}:{secs:02d}"
            except:
                dur_str = "0:00"

            text_lines.append(f"{idx+1}. <b>{title}</b> | {artist} ({dur_str})")

        response_text = "🔎 <b>Found Tracks:</b>\n\n" + "\n".join(text_lines) + "\n\n👇 <b>Tap a number to download:</b>"

        markup = InlineKeyboardMarkup(row_width=5)
        buttons = []
        for idx in range(len(results[:10])):
            buttons.append(InlineKeyboardButton(str(idx+1), callback_data=f"sp_{idx}"))
        markup.add(*buttons)
        
        await bot.edit_message_text(response_text, message.chat.id, wait_msg.message_id, reply_markup=markup, parse_mode="HTML")


    async def process_direct_link(bot, message, url):
        msg = await bot.reply_to(message, "⬇️ Downloading from Spotify...")
        await download_and_send(bot, message.chat.id, url, msg.message_id, message, requester=message.from_user)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sp_"))
    async def handle_callback(call: CallbackQuery):
        try:
            idx = int(call.data.split("_")[1])
            chat_id = call.message.chat.id
            
            if chat_id not in user_search_results or idx >= len(user_search_results[chat_id]):
                await bot.answer_callback_query(call.id, "Session expired or invalid.")
                return

            selected_track = user_search_results[chat_id][idx]
            url = selected_track.get("url")

            await bot.answer_callback_query(call.id, "Starting download...")
            status_msg = await bot.send_message(chat_id, "⏳ Initializing download...")

            await download_and_send(bot, chat_id, url, status_msg.message_id, call.message,
                                    requester=call.from_user, fallback_meta=selected_track)

        except Exception as e:
            print(f"Callback Error: {e}")
            await bot.answer_callback_query(call.id, "Error occurred.")

    async def download_and_send(bot, chat_id, url, message_id_to_edit, message, requester=None, fallback_meta=None):
        try:
            # 1. Try Spotmate to get download link
            dl_link = None
            metadata = {}

            try:
                api_url = f"{DL_SPOTMATE_API}{url}"
                _r1 = await asyncio.to_thread(requests.get, api_url, timeout=30)
                if _r1.status_code == 200 and _r1.text.strip():
                    resp = _r1.json()
                    metadata = resp
                    if resp.get("status") == "success":
                        dl_link = resp.get("download_link")
            except Exception as e:
                print(f"[Spotmate Error] {e}")

            # 2. Fallback to Spowload
            if not dl_link:
                try:
                    api_url = f"{DL_SPOWLOAD_API}{url}"
                    _r2 = await asyncio.to_thread(requests.get, api_url, timeout=30)
                    if _r2.status_code == 200 and _r2.text.strip():
                        resp = _r2.json()
                        if resp.get("status") == "success":
                            dl_link = resp.get("download_link")
                            metadata = resp
                except Exception as e:
                    print(f"[Spowload Error] {e}")
            
            if not dl_link:
                await bot.edit_message_text("❌ Failed to get download link from both APIs.", chat_id, message_id_to_edit)
                return

            if fallback_meta and not metadata.get("title"):
                metadata.update(fallback_meta)

            await bot.edit_message_text(f"⬇️ Downloading: {metadata.get('title', 'Track')}...", chat_id, message_id_to_edit)
            
            title = re.sub(r'[\\/:*?"<>|]', '', metadata.get("title", "audio"))
            cache_dir = os.path.join(os.getcwd(), "cache", "spotify")
            os.makedirs(cache_dir, exist_ok=True)
            filename = os.path.join(cache_dir, f"{title}_{int(time.time())}.mp3")
            thumb_filename = os.path.join(cache_dir, f"thumb_{int(time.time())}.jpg")
            
            # Download Audio
            if not await download_file(dl_link, filename):
                 await bot.edit_message_text("❌ Download failed.", chat_id, message_id_to_edit)
                 return
            
            # Download Thumbnail
            thumb_url = metadata.get("thumbnail")
            has_thumb = False
            if thumb_url:
                has_thumb = await download_file(thumb_url, thumb_filename)

            await bot.edit_message_text("⬆️ Uploading...", chat_id, message_id_to_edit)
            
            try:
                with open(filename, 'rb') as audio:
                    thumb = open(thumb_filename, 'rb') if has_thumb else None
                    
                    user = requester or message.from_user
                    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                    footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                    caption = (
                        f"🎵 <b>{metadata.get('title')}</b>\n"
                        f"👤 {metadata.get('artist')}\n"
                        f"📀 {metadata.get('album')}\n"
                        f"🔗 <a href='{url}'>Listen on Spotify</a>"
                        f"\n{footer}"
                    )
                    
                    await bot.send_audio(
                        chat_id, 
                        audio, 
                        caption=caption,
                        parse_mode="HTML",
                        thumb=thumb,
                        title=metadata.get("title"),
                        performer=metadata.get("artist"),
                        timeout=120
                    )
                    
                    if thumb: thumb.close()

                try:
                    await bot.delete_message(chat_id, message_id_to_edit)
                except: pass
            finally:
                if os.path.exists(filename): os.remove(filename)
                if os.path.exists(thumb_filename): os.remove(thumb_filename)

        except Exception as e:
            print(f"Spotify Logic Error: {e}")
            try:
                await bot.edit_message_text(f"❌ Error: {str(e)}", chat_id, message_id_to_edit)
            except:
                await bot.send_message(chat_id, f"❌ Error: {str(e)}")
