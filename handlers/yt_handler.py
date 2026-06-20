import html
import os
import re
import requests
import subprocess
from telebot import TeleBot
from telebot.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
import threading
import json
import time
from typing import Optional
import tempfile
import mimetypes
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image
from cleanup import cache_manager
import asyncio

CACHE_BASE = os.path.join(os.getcwd(), "cache")
THUMB_CACHE = os.path.join(CACHE_BASE, "yt_thumbnails")
DOWNLOAD_CACHE = os.path.join(CACHE_BASE, "yt_downloads")
os.makedirs(THUMB_CACHE, exist_ok=True)
os.makedirs(DOWNLOAD_CACHE, exist_ok=True)

# === APIs ===
SEARCH_INTERNAL_API = "https://yt-dlx.vercel.app/api/search-internal?q="
SEARCH_FALLBACK_API = "https://yt-dlx.vercel.app/api/search?q="

# === Store user-specific data ===
user_search_results = {}
user_sent_messages = {}

# === Helper Functions ===
def extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|\/|be\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def download_file(url, filename, max_size_mb=50):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
        }
        with await asyncio.to_thread(requests.get, url, stream=True, timeout=120, headers=headers, allow_redirects=True) as r:
            r.raise_for_status()
            
            content_length = r.headers.get('Content-Length')
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                raise ValueError("FileTooLarge")

            downloaded_size = 0
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=16384): # Slightly larger chunk
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if downloaded_size > max_size_mb * 1024 * 1024:
                            raise ValueError("FileTooLarge")
        return True
    except Exception as e:
        if os.path.exists(filename):
            try: os.remove(filename)
            except: pass
        if isinstance(e, ValueError) and str(e) == "FileTooLarge":
            raise e
        print(f"[!] Direct download failed: {e}")
        return False

async def download_thumbnail(url, chat_id, index):
    """Download thumbnail and convert to JPG for Telegram compatibility"""
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        response.raise_for_status()
        
        temp_dir = os.path.join(THUMB_CACHE, str(chat_id))
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"thumb_{index}.jpg")
        
        img = Image.open(BytesIO(response.content))
        if img.mode in ("RGBA", "P"): 
             img = img.convert("RGB")
             
        img.save(file_path, "JPEG", quality=90)
            
        if os.path.getsize(file_path) == 0:
            os.remove(file_path)
            return None
            
        return file_path
    except Exception as e:
        print(f"[!] Thumbnail download/conversion failed: {e}")
        return None

def cleanup_thumbnails(chat_id):
    """Clean up downloaded thumbnails for a chat"""
    try:
        temp_dir = os.path.join(THUMB_CACHE, str(chat_id))
        if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                try:
                    os.remove(file_path)
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
    except Exception as e:
        print(f"[!] Cleanup failed: {e}")

async def fetch_insvid_download_url(video_url: str, file_type: str) -> Optional[dict]:
    video_id = extract_video_id(video_url)
    if not video_id:
        return None

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://ac.insvid.com',
        'priority': 'u=1, i',
        'referer': f'https://ac.insvid.com/widget?url=https://www.youtube.com/watch?v={video_id}&el=185',
        'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-storage-access': 'active',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    }

    json_data = {
        'id': video_id,
        'fileType': file_type,
    }

    try:
        response = await asyncio.to_thread(
            requests.post,
            'https://ac.insvid.com/converter',
            headers=headers,
            json=json_data,
            timeout=30
        )
        if response.status_code == 200:
            title = res_data.get("title") or "YouTube Video"
            if file_type == 'MP3':
                if res_data.get("status") == "ok" and res_data.get("link"):
                    return {"url": res_data.get("link"), "title": title}
            else:
                formats = res_data.get("formats", [])
                if res_data.get("status") == "success" and formats:
                    selected_format = None
                    for f in formats:
                        if f.get("url"):
                            selected_format = f
                            # Prefer 720p or 360p if available
                            if f.get("qualityLabel") in ("720p", "360p"):
                                break
                    if selected_format:
                        return {"url": selected_format.get("url"), "title": title}
    except Exception as e:
        print(f"[fetch_insvid_download_url ERROR]: {e}")
    return None

def register(bot: TeleBot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    FILENAME_SANITIZE_PATTERN = r'[\\/:*?"<>|]'

    @custom_command_handler("yt")
    async def yt_command(message: Message):
        cleanup_thumbnails(message.chat.id)
            
        if not message.text:
            await bot.reply_to(message, f"Please enter something to search on YouTube.\nUsage: `{command_prefixes_list[0]}yt <search query>`", parse_mode="Markdown")
            return
        
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             query_raw = " ".join(parts_split[1:]).strip()
        else:
             query_raw = ""
        
        query = query_raw
        
        wait_msg = await bot.reply_to(message, "🔍 Searching...")

        results = []
        is_direct_link = False

        # === 1. DIRECT LINK HANDLING (Skip Search List) ===
        if "http" in query and (("youtube.com" in query) or ("youtu.be" in query)):
            is_direct_link = True
            vid_id = extract_video_id(query)
            
            video_metadata = None
            
            # 1.3 Try Search APIs (Fallback 2 - by ID)
            if not video_metadata and vid_id:
                try:
                    search_apis = [SEARCH_INTERNAL_API, SEARCH_FALLBACK_API]
                    for api in search_apis:
                        resp = await asyncio.to_thread(requests.get, api + vid_id, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("results"):
                                # Look for exact ID match
                                for res in data["results"]:
                                    if res.get("id") == vid_id:
                                        video_metadata = {
                                            "id": vid_id,
                                            "title": re.sub(FILENAME_SANITIZE_PATTERN, '', res.get("title", "YouTube Video")),
                                            "duration": str(res.get("duration") or res.get("duration_formatted") or "N/A"),
                                            "thumbnail": res.get("thumbnail"),
                                            "channel": res.get("channel", "YouTube"),
                                            "url": query
                                        }
                                        break
                        if video_metadata: break
                except Exception as e:
                    print(f"[!] Search fallback Failed: {e}")

            if video_metadata:
                user_search_results[message.chat.id] = [video_metadata]
                
                thumb_url = video_metadata["thumbnail"]
                thumb_path = None
                if thumb_url:
                    thumb_path = await download_thumbnail(thumb_url, message.chat.id, 0)
                
                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                
                caption = f"🎬 <b>{video_metadata['title']}</b>\n⏱ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: {video_metadata['duration']}\n👤 {video_metadata['channel']}\n\nSelect Format:\n{footer}"
                
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"download_0_audio"),
                    InlineKeyboardButton("🎬 Video (360p)", callback_data=f"download_0_video")
                )
                
                if thumb_path:
                    try:
                        with open(thumb_path, 'rb') as f:
                            await bot.send_photo(message.chat.id, f, caption=caption, reply_markup=markup)
                    except:
                        await bot.send_message(message.chat.id, caption, reply_markup=markup)
                else:
                    await bot.send_message(message.chat.id, caption, reply_markup=markup)
                
                await bot.delete_message(message.chat.id, wait_msg.message_id)
                return
            else:
                await bot.edit_message_text("❌ Video info not found. Please check the link.", chat_id=message.chat.id, message_id=wait_msg.message_id)
                return

        # === 2. Internal Search API ===
        if not results:
            try:
                resp = await asyncio.to_thread(requests.get, SEARCH_INTERNAL_API + query, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                if data.get("results"):
                    for item in data["results"][:10]:
                        results.append({
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "duration": item.get("duration"),
                            "thumbnail": item.get("thumbnail"),
                            "channel": item.get("channel"),
                            "url": item.get("url") or f"https://www.youtube.com/watch?v={item.get('id')}"
                        })
            except Exception as e:
                print(f"[!] Internal Search Failed: {e}")
        
        # === 3. Fallback Search API ===
        if not results:
            try:
                resp = await asyncio.to_thread(requests.get, SEARCH_FALLBACK_API + query, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                if data.get("results"):
                    for item in data["results"][:10]:
                        results.append({
                            "id": item.get("id"),
                            "title": item.get("title"),
                            "duration": item.get("duration_formatted"),
                            "thumbnail": item.get("thumbnail"),
                            "channel": item.get("channel"),
                            "url": item.get("url") or f"https://www.youtube.com/watch?v={item.get('id')}"
                        })
            except Exception as e:
                print(f"[!] Fallback Search Failed: {e}")

        if not results:
            await bot.edit_message_text("❌ No results found.", chat_id=message.chat.id, message_id=wait_msg.message_id)
            return

        user_search_results[message.chat.id] = results

        # === Process Results & Send ===
        try:
            await bot.edit_message_text("📥 Processing results...", chat_id=message.chat.id, message_id=wait_msg.message_id)

            markup = InlineKeyboardMarkup(row_width=5)
            buttons = [InlineKeyboardButton(str(i+1), callback_data=f"select_{i}") for i in range(len(results))]
            markup.add(*buttons)
            
            desc_text = "🔍 <b>𝗦𝗲𝗮𝗿𝗰𝗵 𝗥𝗲𝘀𝘂𝗹𝘁𝘀</b>\n\n"
            for i, video in enumerate(results):
                title = html.escape(re.sub(FILENAME_SANITIZE_PATTERN, '', video["title"]))
                duration = video.get("duration", "Unknown")
                channel = html.escape(video.get("channel", "Unknown"))
                desc_text += f"<b>{i+1}.</b> {title}\n⏱ {duration} | 👤 {channel}\n\n"
            
            user = message.from_user
            username = html.escape(f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id))
            footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
            desc_text += "\n" + footer

            await bot.send_message(message.chat.id, desc_text, reply_markup=markup, disable_web_page_preview=True)
            await bot.delete_message(message.chat.id, wait_msg.message_id)

        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
            await bot.reply_to(message, "❌ Error processing search results.")

    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("select_"))
    async def handle_select(call: CallbackQuery):
        if check_usage_limit and not await check_usage_limit(call.message, "yt"):
            return
            
        try:
            idx = int(call.data.split("_")[1])
            chat_id = call.message.chat.id

            if chat_id not in user_search_results:
                await bot.answer_callback_query(call.id, "Session expired. Please search again.")
                return
            
            if idx >= len(user_search_results[chat_id]):
                await bot.answer_callback_query(call.id, "Invalid selection")
                return

            video = user_search_results[chat_id][idx]
            title = video["title"]
            duration = video.get("duration", "Unknown")
            
            user = call.message.from_user # Note: this might be bot if message was edited, but usually we use call.from_user for requester
            user = call.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            caption = f"🎬 <b>{title}</b>\n⏱ 𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: {duration}\n\nSelect Format:\n{footer}"
            
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"download_{idx}_audio"),
                InlineKeyboardButton("🎬 Video (720p/360p)", callback_data=f"download_{idx}_video")
            )
            
            thumb_path_cached = None
            tpath = os.path.join("cache", "yt_thumbnails", str(chat_id), f"thumb_{idx}.jpg")
            if os.path.exists(tpath):
                thumb_path_cached = tpath
            
            if not thumb_path_cached and video.get("thumbnail"):
                 if "Direct Link" not in call.message.text: 
                     await bot.answer_callback_query(call.id, "Loading thumbnail...")
                 thumb_path_cached = await download_thumbnail(video.get("thumbnail"), chat_id, idx)
            
            if thumb_path_cached:
                try:
                    with open(thumb_path_cached, 'rb') as f:
                        await bot.send_photo(chat_id, f, caption=caption, reply_markup=markup)
                except Exception as e:
                    print(f"[SELECT SEND ERROR] {e}")
                    await bot.send_message(chat_id, caption, reply_markup=markup)
            else:
                 await bot.send_message(chat_id, caption, reply_markup=markup)
                
            await bot.answer_callback_query(call.id)
            
        except Exception as e:
            print(f"[SELECT ERROR] {e}")
            await bot.answer_callback_query(call.id, "Error processing selection")

    async def process_download(bot, chat_id, idx, choice, message, requester=None):
        wait_msg = None
        filename = None
        thumb_path = None
        
        try:
            wait_msg = await bot.send_message(chat_id, f"📥 Generating download link... please wait.")
            
            video = user_search_results.get(chat_id, [])[idx]
            video_url = video["url"]
            title = re.sub(r'[\\/:*?"<>|]', '', video["title"])

            download_url = None
            success = False
            source_api = "insvid"

            if choice == "video":
                # 1. Main API: ac.insvid.com
                try:
                    res_info = await fetch_insvid_download_url(video_url, "mp4")
                    if res_info and res_info.get("url"):
                        download_url = res_info["url"]
                        if res_info.get("title"):
                            title = re.sub(r'[\\/:*?"<>|]', '', res_info["title"])
                        success = True
                        source_api = "insvid"
                except Exception as e:
                    print(f"[VIDEO INSVID API ERROR] {e}")

            elif choice == "audio":
                # 1. Main API: ac.insvid.com
                try:
                    res_info = await fetch_insvid_download_url(video_url, "MP3")
                    if res_info and res_info.get("url"):
                        download_url = res_info["url"]
                        if res_info.get("title"):
                            title = re.sub(r'[\\/:*?"<>|]', '', res_info["title"])
                        success = True
                        source_api = "insvid"
                except Exception as e:
                    print(f"[AUDIO INSVID API ERROR] {e}")

            if not success or not download_url:
                await bot.edit_message_text("❌ Could not generate download link.", chat_id=chat_id, message_id=wait_msg.message_id)
                return

            ext = "mp4" if choice == "video" else "mp3"
            filename = os.path.join(DOWNLOAD_CACHE, f"{title}.{ext}")
            
            await bot.edit_message_text(f"⬇️ Downloading file... \n\n⚠️ If file is too large, a link will be provided.", chat_id=chat_id, message_id=wait_msg.message_id)
            
            try:
                download_success = await download_file(download_url, filename, max_size_mb=50)
            except ValueError as e:
                if str(e) == "FileTooLarge":
                    if choice == "video":
                        msg_large = "⚠️ File is too large (>50MB). Providing direct download link..."
                        await bot.edit_message_text(msg_large, chat_id=chat_id, message_id=wait_msg.message_id)
                        
                        final_url = download_url
                        await bot.edit_message_text(f"⚠️ File is too large (>50MB).\n\n🔗 <b><a href='{final_url}'>Direct Download Link</a></b>", chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")
                    else:
                        await bot.edit_message_text(f"⚠️ File is too large (>50MB).\n\n🔗 <b><a href='{download_url}'>Direct Download Link</a></b>", chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")
                    return
                else: 
                    raise e
 
            if download_success:
                await bot.edit_message_text("📤 Uploading file...", chat_id=chat_id, message_id=wait_msg.message_id)
                try:
                    with open(filename, 'rb') as f:
                        user = requester or message.from_user
                        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                        footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                        if choice == "video":
                            await bot.send_video(chat_id, f, caption=f"🎬 {title}\n{footer}", supports_streaming=True, timeout=900, parse_mode="HTML")
                        else:
                            thumb_file = None
                            tpath = os.path.join(THUMB_CACHE, str(chat_id), f"thumb_{idx}.jpg")
                            if os.path.exists(tpath):
                                try: thumb_file = open(tpath, 'rb')
                                except: pass
 
                            await bot.send_audio(chat_id, f, caption=f"🎵 {title}\n{footer}", title=title, thumb=thumb_file, timeout=900, parse_mode="HTML")
                            if thumb_file: thumb_file.close()
 
                    await bot.delete_message(chat_id, wait_msg.message_id)
                except Exception as e:
                    print(f"[UPLOAD ERROR] {e}")
                    await bot.edit_message_text(f"❌ Could not upload file to Telegram.\n\n🔗 <b><a href='{download_url}'>Direct Download Link</a></b>", chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")
            else:
                await bot.edit_message_text(f"⚠️ Could not be downloaded.\n\n🔗 <b><a href='{download_url}'>Direct Download Link</a></b>", chat_id=chat_id, message_id=wait_msg.message_id, parse_mode="HTML")

        except Exception as e:
            print(f"[PROCESS ERROR] {e}")
            if wait_msg:
                await bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=chat_id, message_id=wait_msg.message_id)
        finally:
            if filename and os.path.exists(filename):
                try: os.remove(filename)
                except: pass

    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("download_"))
    async def handle_download(call: CallbackQuery):
        try:
            parts = call.data.split("_")
            idx = int(parts[1])
            choice = parts[2]
            chat_id = call.message.chat.id
            if chat_id not in user_search_results:
                await bot.answer_callback_query(call.id, "Session expired. Please search again.")
                return

            await bot.answer_callback_query(call.id, "Checking availability...")
            try:
                await bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            asyncio.ensure_future(process_download(bot, chat_id, idx, choice, call.message, requester=call.from_user))

        except Exception as e:
            print(f"[CALLBACK ERROR] {e}")
            await bot.answer_callback_query(call.id, "Error")
