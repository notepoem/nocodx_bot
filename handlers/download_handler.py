import os
import html
import re
import requests
import yt_dlp
from telebot.types import InputMediaPhoto, InputMediaVideo
import asyncio

URL_RE = re.compile(r'(https?://[^\s]+)')

CACHE_DIR = os.path.join(os.getcwd(), "cache", "download")
os.makedirs(CACHE_DIR, exist_ok=True)

APIS = {
    "facebook": {
        "domains": ["facebook.com", "fb.watch", "fb.com"],
        "url": "https://no-api.bbinl.site/api/facebook?url=",
        "type": "json_data_links" 
    },
    "instagram": {
        "domains": ["instagram.com", "instagr.am"],
        "url": "https://no-api.bbinl.site/api/instagram?url=",
        "type": "json_data_media"
    },
    "twitter": {
        "domains": ["twitter.com", "x.com"],
        "url": "https://no-api.bbinl.site/api/twitter?url=",
        "type": "json_media_variants"
    },
    "pinterest": {
        "domains": ["pinterest.com", "pin.it"],
        "url": "https://no-api.bbinl.site/api/pinterest?url=",
        "type": "json_video_or_image"
    },
    "threads": {
        "domains": ["threads.net", "threads.com"],
        "url": "https://no-api.bbinl.site/api/threads?url=",
        "type": "json_data_media_list"
    },
    "tiktok": {
        "domains": ["tiktok.com", "vt.tiktok.com", "vm.tiktok.com"],
        "url": "https://no-api.bbinl.site/api/tiktok?url=",
        "type": "json_tiktok"
    },
    "youtube": {
        "domains": ["youtube.com", "youtu.be"],
        "url": "https://yt-dlx.vercel.app/api/socialcat?url=",
        "type": "json_socialcat"
    },
    "spotify": {
        "domains": ["open.spotify.com", "spotify.link"],
        "url": "https://spoti-dlx.vercel.app/api/spotmate?url=",
        "type": "json_spotify"
    },
    "snapchat": {
        "domains": ["snapchat.com"],
        "url": "https://no-api.bbinl.site/api/snapchat?url=",
        "type": "json_snapchat"
    }
}

COMMAND_ALIASES = {
    "dl": ["dl"],
    "facebook": ["fb", "facebook"],
    "instagram": ["ig", "insta", "instagram"],
    "twitter": ["x", "twitter"],
    "pinterest": ["pin", "pinterest"],
    "threads": ["th", "threads"],
    "tiktok": ["tt", "tiktok"],
    "youtube": ["youtube"],
    "spotify": ["spotify", "spoti"],
    "snapchat": ["snap", "snapchat"]
}

def _detect_platform(url: str):
    """Detects the platform key based on the URL domain."""
    for name, config in APIS.items():
        for domain in config["domains"]:
            if domain in url:
                return name
    return None

def download_with_yt_dlp(url: str, download_dir: str = CACHE_DIR, extra_opts: dict = None) -> str:
    """Fallback downloader using yt-dlp."""
    os.makedirs(download_dir, exist_ok=True)
    opts = {
        "quiet": True,
        "noplaylist": True,
        "geo_bypass": True,
        "outtmpl": os.path.join(download_dir, "%(title).100s-%(id)s.%(ext)s"),
        "format": "bestvideo+bestaudio/best", 
    }
    
    if extra_opts:
        opts.update(extra_opts)
    
    cookies_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cookies')
    for filename in os.listdir(cookies_dir) if os.path.exists(cookies_dir) else []:
        if filename.endswith(".txt"):
             pass

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        return path


async def download_file(url: str, filename: str, download_dir: str = CACHE_DIR, max_size_mb: int = 50):
    """Downloads a file from a URL to the specified directory."""
    os.makedirs(download_dir, exist_ok=True)
    path = os.path.join(download_dir, filename)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        with await asyncio.to_thread(requests.get, url, stream=True, timeout=60, headers=headers) as r:
            r.raise_for_status()
            
            content_length = r.headers.get('Content-Length')
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                raise ValueError("FileTooLarge")

            downloaded_size = 0
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if downloaded_size > max_size_mb * 1024 * 1024:
                        raise ValueError("FileTooLarge")
        return path
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        raise e

def format_caption(title, author, source, url, message):
    """Formats a rich caption."""
    title = html.escape(str(title) if title else "Unknown")
    author = html.escape(str(author) if author else "Unknown")
    source = html.escape(str(source).capitalize() if source else "Source")
    
    user = message.from_user
    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
    footer = f"\n\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

    caption = f"•──────────────────────•\n🎬 <b>𝗧𝗶𝘁𝗹𝗲:</b> {title}\n"
    if author:
        caption += f"👤 <b>𝗔𝘂𝘁𝗵𝗼𝗿:</b> {author}\n"
    caption += f"🔗 <b>𝗦𝗼𝘂𝗿𝗰𝗲:</b> <a href='{url}'>{source}</a>"
    caption += footer
    return caption

async def process_youtube_download(bot, message, url):
    """Fresh implementation for YouTube downloading."""
    msg = await bot.reply_to(message, "⬇️ Fetching data from YouTube...", parse_mode="HTML")
    
    async def get_fresh_link(original_url):
         try:
             r = await asyncio.to_thread(requests.get, f"https://yt-dlx.vercel.app/api/socialcat?url={original_url}&format=720", timeout=30)
             if r.ok and r.json().get("success"):
                 urls = r.json().get("mediaUrls", [])
                 if urls: return urls[0]
         except: pass
         try:
             r = await asyncio.to_thread(requests.get, f"https://yt-dlx.vercel.app/api/savenow?url={original_url}&format=720", timeout=30)
             if r.ok and r.json().get("success"):
                 return r.json().get("download_url")
         except: pass
         return None

    video_url = None
    caption_title = "YouTube Video"
    
    # 1. Main API
    try:
        r = await asyncio.to_thread(requests.get, f"https://yt-dlx.vercel.app/api/socialcat?url={url}&format=720", timeout=30)
        data = r.json()
        if data.get("success"):
            urls = data.get("mediaUrls", [])
            if urls: 
                video_url = urls[0]
                caption_title = data.get("caption") or "YouTube Video"
    except Exception as e:
        print(f"Main API Error: {e}")

    # 2. Fallback API
    if not video_url:
        try:
             r = await asyncio.to_thread(requests.get, f"https://yt-dlx.vercel.app/api/savenow?url={url}&format=720", timeout=30)
             data = r.json()
             if data.get("success"):
                 video_url = data.get("download_url")
                 caption_title = "YouTube Video/Short"
        except Exception as e:
             print(f"Fallback API Error: {e}")

    if not video_url:
        await bot.edit_message_text("❌ Failed to fetch video link from all APIs.", message.chat.id, msg.message_id)
        return

    # 3. Download & Upload
    await bot.edit_message_text("⬇️ Downloading...", message.chat.id, msg.message_id)
    filename = f"youtube_{message.message_id}.mp4"
    file_path = None
    
    try:
        file_path = await download_file(video_url, filename, max_size_mb=50)
        
        if os.path.exists(file_path) and os.path.getsize(file_path) < 10 * 1024:
             raise ValueError("FileTooSmall")

        await bot.edit_message_text("⬆️ Uploading...", message.chat.id, msg.message_id)
        caption = format_caption(caption_title, "YouTube", "YouTube", url, message)
        
        try:
            with open(file_path, 'rb') as f:
                await bot.send_video(message.chat.id, f, caption=caption, parse_mode="HTML", timeout=600)
            await bot.delete_message(message.chat.id, msg.message_id)
        except Exception as upload_error:
            print(f"Upload failed: {upload_error}")
            fresh = await get_fresh_link(url)
            dl_link = fresh if fresh else video_url
            await bot.edit_message_text(f"⚠️ Upload failed (Timeout/Size).\n👇 Download directly:\n🔗 <a href='{dl_link}'>Download Now</a>", message.chat.id, msg.message_id, parse_mode="HTML")

    except ValueError as e:
        err_str = str(e)
        if err_str == "FileTooLarge":
             await bot.edit_message_text("⚠️ File >50MB. Fetching fresh link...", message.chat.id, msg.message_id)
             fresh = await get_fresh_link(url)
             if fresh:
                 await bot.edit_message_text(f"⚠️ File too large for Telegram API.\n👇 Here is your direct link:\n🔗 <a href='{fresh}'>Download Now</a>", message.chat.id, msg.message_id, parse_mode="HTML")
             else:
                 await bot.edit_message_text("⚠️ File too large and failed to generate fresh link.", message.chat.id, msg.message_id)
        
        elif err_str == "FileTooSmall":
             await bot.edit_message_text("⚠️ Invalid file content. Retrying with fresh link...", message.chat.id, msg.message_id)
             fresh = await get_fresh_link(url)
             if fresh and fresh != video_url:
                 try:
                     if os.path.exists(file_path): os.remove(file_path)
                     file_path = await download_file(fresh, filename, max_size_mb=50)
                     
                     await bot.edit_message_text("⬆️ Uploading...", message.chat.id, msg.message_id)
                     caption = format_caption(caption_title, "YouTube", "YouTube", url, message)
                     with open(file_path, 'rb') as f:
                        await bot.send_video(message.chat.id, f, caption=caption, parse_mode="HTML", timeout=600)
                     await bot.delete_message(message.chat.id, msg.message_id)
                 except Exception as retry_error:
                     if "FileTooLarge" in str(retry_error): raise retry_error 
                     await bot.edit_message_text(f"⚠️ Upload failed on retry.\n🔗 <a href='{fresh}'>Download Link</a>", message.chat.id, msg.message_id, parse_mode="HTML")
                 except ValueError as e2:
                     if str(e2) == "FileTooLarge":
                         await bot.edit_message_text(f"⚠️ File too large.\n🔗 <a href='{fresh}'>Download Link</a>", message.chat.id, msg.message_id, parse_mode="HTML")
                     else:
                         await bot.edit_message_text("❌ Failed to download fresh link.", message.chat.id, msg.message_id)
                 except Exception as ex:
                     await bot.edit_message_text(f"❌ Error during retry: {ex}", message.chat.id, msg.message_id)
             else:
                 await bot.edit_message_text("❌ Failed to fetch valid video content.", message.chat.id, msg.message_id)
        else:
             await bot.edit_message_text(f"❌ Error: {err_str}", message.chat.id, msg.message_id)

    except Exception as e:
        await bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg.message_id)
    
    finally:
        if file_path and os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass

async def process_api_download(bot, message, url: str, platform: str):
    """Process download using the configured API."""
    config = APIS[platform]
    msg = await bot.reply_to(message, f"⬇️ Fetching data from {platform.capitalize()}...")
    
    attempts = []
    
    if platform == "spotify":
        attempts.append({"url": "https://spoti-dlx.vercel.app/api/spotmate?url=", "type": "json_spotify"})
        attempts.append({"url": "https://spoti-dlx.vercel.app/api/spowload?url=", "type": "json_spowload"})
    else:
        attempts.append(config)

    data = None
    media_group = []
    title = ""
    author = ""
    thumb_url = None
    
    success = False
    
    for attempt in attempts:
        if success: break
        
        retries = attempt.get("retries", 1)
        current_api_url = f"{attempt['url']}{url}"
        api_type = attempt["type"]

        for _ in range(retries):
            try:
                response = await asyncio.to_thread(requests.get, current_api_url, timeout=120) # Increased timeout for slow APIs
                response.raise_for_status()
                data = response.json()
                
                if api_type == "json_data_links": # Facebook
                    if data.get("success"):
                        d = data.get("data", {})
                        links = d.get("links", {})
                        m_url = links.get("hd") or links.get("sd")
                        if m_url:
                            media_group.append({"type": "video", "url": m_url})
                        title = d.get("title") or "Facebook Video"
                        author = d.get("author", {}).get("name", "")
                        if media_group: success = True

                elif api_type == "json_data_media": # Instagram
                    if data.get("success"):
                        d = data.get("data", {})
                        title = d.get("caption", "Instagram")
                        author = d.get("author", {}).get("full_name") or d.get("author", {}).get("username", "")
                        
                        src = d.get("thumbnail_src")
                        if isinstance(src, list) and src:
                            for img_url in src:
                                media_group.append({"type": "image", "url": img_url})
                        elif d.get("video_url"):
                            media_group.append({"type": "video", "url": d.get("video_url")})
                        elif isinstance(src, str):
                            media_group.append({"type": "image", "url": src})
                        if media_group: success = True

                elif api_type == "json_media_variants": # Twitter
                    if data.get("success"):
                        media = data.get("media", {})
                        title = data.get("text", "Twitter")
                        author = data.get("author", {}).get("name", "")
                        
                        if media.get("type") == "video":
                            variants = media.get("variants", [])
                            variants.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
                            if variants:
                                media_group.append({"type": "video", "url": variants[0].get("url")})
                        elif media.get("type") == "image":
                            images = media.get("images", [])
                            for img in images:
                                media_group.append({"type": "image", "url": img})
                        if media_group: success = True

                elif api_type == "json_video_or_image": # Pinterest
                    if data.get("status") == "success":
                        title = data.get("pin", {}).get("title", "Pinterest")
                        author = data.get("author", {}).get("displayName", "")
                        if data.get("video"):
                            media_group.append({"type": "video", "url": data.get("video", {}).get("sources", {}).get("mp4", {}).get("url")})
                        elif data.get("pin", {}).get("images"):
                            images = data.get("pin", {}).get("images", {})
                            for key in ['orig', 'large', 'medium']:
                                if key in images:
                                    media_group.append({"type": "image", "url": images[key].get("url")})
                                    break
                        if media_group: success = True

                elif api_type == "json_data_media_list": # Threads
                    if data.get("success"):
                        d = data.get("data", {})
                        title = d.get("caption", "Threads")
                        author = d.get("author", {}).get("username", "")
                        media_list = d.get("media", [])
                        if media_list:
                            for item in media_list:
                                if item.get("type") == "video":
                                    media_group.append({"type": "video", "url": item.get("video_url") or item.get("url")})
                                else:
                                    media_group.append({"type": "image", "url": item.get("url")})
                        if media_group: success = True

                elif api_type == "json_tiktok": # TikTok
                    if data.get("status") == "success" or True:
                        media_data = data.get("media_files", {})
                        main = media_data.get("main_links", {})
                        m_url = main.get("no_watermark") or main.get("watermarked")
                        if m_url:
                            media_group.append({"type": "video", "url": m_url})
                        video_data = data.get("video_data", {})
                        title = video_data.get("title", "TikTok")
                        author = video_data.get("author", {}).get("name", "")
                        if media_group: success = True

                elif api_type == "json_spotify": # Spotify Primary
                    if data.get("status") == "success":
                        media_group.append({
                            "type": "audio", 
                            "url": data.get("download_link"), 
                            "thumb": data.get("thumbnail"),
                            "album": data.get("album")
                        })
                        title = data.get("title", "")
                        author = data.get("artist", "")
                        success = True

                elif api_type == "json_spowload": # Spotify Fallback
                    if data.get("status") == "success":
                         media_group.append({
                             "type": "audio",
                             "url": data.get("download_link"),
                             "thumb": data.get("thumbnail"),
                             "album": data.get("album")
                         })
                         title = data.get("title", "")
                         author = data.get("artist", "")
                         success = True

                elif api_type == "json_snapchat": # Snapchat
                    if data.get("success"):
                        d = data.get("data", {})
                        media_url = d.get("video_url")
                        thumb_url = d.get("thumbnail")
                        if media_url:
                            media_group.append({
                                "type": "video",
                                "url": media_url,
                                "thumb": thumb_url
                            })
                            success = True
                        title = "Snapchat Video"
                
                if success: break
            
            except Exception as inner_e:
                print(f"Attempt failed ({api_type}): {inner_e}")
                pass # Try next retry or next API
    
    if not success or not media_group:
        await bot.edit_message_text("❌ Failed to fetch media from all available APIs.", message.chat.id, msg.message_id)
        return

    await bot.edit_message_text(f"⬇️ Downloading content...", message.chat.id, msg.message_id)
        
    caption_text = format_caption(title, author, platform, url, message)
    
    if len(media_group) == 1:
        item = media_group[0]
        media_type = item["type"]
        ext = "mp4"
        if media_type == "image": ext = "jpg"
        elif media_type == "audio": ext = "mp3"
        
        filename = f"{platform}_{message.message_id}.{ext}"
        
        try:
             file_path = await download_file(item["url"], filename)
             
             file_size = os.path.getsize(file_path) 
             
             if file_size < 5 * 1024:
                 is_m3u8 = False
                 try:
                     with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                         content_preview = f.read(500)
                         if "#EXTM3U" in content_preview:
                             is_m3u8 = True
                         else:
                             print(f"Downloaded file too small. Preview: {content_preview}")
                 except: pass
                 
                 if is_m3u8:
                     await bot.edit_message_text("🔄 Stream detected, processing...", message.chat.id, msg.message_id)
                     if os.path.exists(file_path): os.remove(file_path)
                     file_path = download_with_yt_dlp(item["url"], extra_opts={"format": None})
                     file_size = os.path.getsize(file_path)
                 else: 
                     raise ValueError("FileTooSmall")

             await bot.edit_message_text(f"⬆️ Uploading {media_type}...", message.chat.id, msg.message_id)
             with open(file_path, 'rb') as f:
                 if media_type == "video":
                     await bot.send_video(message.chat.id, f, caption=caption_text, parse_mode="HTML", timeout=600)
                 elif media_type == "image":
                     await bot.send_photo(message.chat.id, f, caption=caption_text, parse_mode="HTML")
                 elif media_type == "audio":
                     await bot.send_audio(message.chat.id, f, caption=caption_text, parse_mode="HTML", 
                                  title=title, performer=author, timeout=600)
             
             await bot.delete_message(message.chat.id, msg.message_id)

        except ValueError as e:
             if str(e) == "FileTooLarge":
                  await bot.edit_message_text(f"⚠️ File is too large (>50MB) for Telegram Bot API.\n🔗 <a href='{item['url']}'>Download Link</a>\n🔗 <a href='{url}'>Source Link</a>", message.chat.id, msg.message_id, parse_mode="HTML")
                  if 'file_path' in locals() and os.path.exists(file_path): os.remove(file_path)
                  return

             if str(e) == "FileTooSmall":
                  await bot.edit_message_text(f"⚠️ Content unavailable/invalid.\n🔗 <a href='{url}'>Source Link</a>", message.chat.id, msg.message_id, parse_mode="HTML")
                  if 'file_path' in locals() and os.path.exists(file_path): os.remove(file_path)
                  return

        except Exception as e:
             print(f"Process failed: {e}")
             error_msg = "Download/Upload failed"
             if "502" in str(e): error_msg = "Source Server Error (502)"
             
             await bot.edit_message_text(f"⚠️ {error_msg}.\n🔗 <a href='{url}'>Source Link</a>", message.chat.id, msg.message_id, parse_mode="HTML")
        
        finally:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        
        return

    downloaded_files = [] 
    input_media = []
    
    try:
        for idx, item in enumerate(media_group):
            ext = "mp4" if item["type"] == "video" else "jpg"
            filename = f"{platform}_{message.message_id}_{idx}.{ext}"
            path = await download_file(item["url"], filename)
            downloaded_files.append((path, item["type"]))
            
            if idx == 0:
                if item["type"] == "video":
                    input_media.append(InputMediaVideo(open(path, 'rb'), caption=caption_text, parse_mode="HTML"))
                else:
                    input_media.append(InputMediaPhoto(open(path, 'rb'), caption=caption_text, parse_mode="HTML"))
            else:
                if item["type"] == "video":
                    input_media.append(InputMediaVideo(open(path, 'rb')))
                else:
                    input_media.append(InputMediaPhoto(open(path, 'rb')))

        await bot.edit_message_text("⬆️ Uploading album...", message.chat.id, msg.message_id)
        await bot.send_media_group(message.chat.id, input_media)
        await bot.delete_message(message.chat.id, msg.message_id) # Delete loading message on success
        
    except Exception as e:
        print(f"Album upload failed: {e}")
        links_text = "\n".join([f"🔗 <a href='{m['url']}'>Link {i+1}</a>" for i, m in enumerate(media_group)])
        await bot.edit_message_text(f"⚠️ Album upload failed.\n{links_text}", message.chat.id, msg.message_id, parse_mode="HTML")

    finally:
        # Cleanup
        for path, _ in downloaded_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass 
        
        del input_media


async def start_ytdlp(bot, message, url):
    msg = await bot.reply_to(message, "⏳ Trying with yt-dlp...")
    try:
        path = download_with_yt_dlp(url)
        if os.path.exists(path):
            try:
                await bot.send_video(message.chat.id, open(path, 'rb'), caption="✅ Download successful (yt-dlp)", timeout=600)
                await bot.delete_message(message.chat.id, msg.message_id)
            except Exception as e:
                 try:
                     await bot.send_document(message.chat.id, open(path, 'rb'), caption="✅ Download successful (Document)", timeout=600)
                     await bot.delete_message(message.chat.id, msg.message_id)
                 except:
                     await bot.edit_message_text(f"⚠️ Downloaded but failed to upload (Size/Timeout). Source: {url}", message.chat.id, msg.message_id)
            finally:
                if os.path.exists(path):
                    os.remove(path)
        else:
             await bot.edit_message_text("❌ yt-dlp download failed.", message.chat.id, msg.message_id)
    except Exception as e:
        await bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, msg.message_id)

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    
    all_commands = []
    for cmds in COMMAND_ALIASES.values():
        all_commands.extend(cmds)
    
    all_commands = list(set(all_commands))

    @custom_command_handler(*all_commands)
    async def handle_download_command(message):
        if check_usage_limit and not await check_usage_limit(message, "Download"):
            return

        text = message.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
             await bot.reply_to(message, "⚠️ Please provide a link.\nExample: `/dl https://...`", parse_mode="Markdown")
             return
        
        url_match = URL_RE.search(parts[1])
        if not url_match:
             await bot.reply_to(message, "⚠️ No valid link found.", parse_mode="Markdown")
             return
        
        url = url_match.group(0)
        platform = _detect_platform(url)

        if platform:
            if platform == "youtube":
                await process_youtube_download(bot, message, url)
            else:
                await process_api_download(bot, message, url, platform)
        else:
            await start_ytdlp(bot, message, url)