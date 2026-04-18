import telebot
import yt_dlp
import datetime
import html
import asyncio
import requests
import io

CAPTION_LIMIT = 1024

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @custom_command_handler("ytinfo", "yth", "ytdata")
    async def handle_yt_metadata(message):
        if check_usage_limit and not await check_usage_limit(message, "YouTubeInfo"):
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await bot.reply_to(message, "⚠️ Usage: `/ytinfo <video_link>`")
            return

        url = args[1].strip()
        status_msg = await bot.reply_to(message, "🔍 Fetching video metadata...")

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios'],
                    'skip': ['dash', 'hls'],
                }
            }
        }

        try:
            info = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise Exception("yt-dlp returned no information.")

            title       = info.get('title', 'N/A')
            channel     = info.get('uploader', 'N/A')
            views       = info.get('view_count', 0) or 0
            likes       = info.get('like_count', 0) or 0
            duration    = info.get('duration', 0) or 0
            upload_date = info.get('upload_date', 'N/A')
            description = info.get('description', '') or ''
            tags        = info.get('tags', []) or []
            video_id    = info.get('id')

            if upload_date and len(upload_date) == 8:
                upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

            duration_str = str(datetime.timedelta(seconds=int(duration)))

            thumbnails = info.get('thumbnails', []) or []
            thumb_url  = thumbnails[-1]['url'] if thumbnails else None

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = (
                f"\n•──────────────────────•\n"
                f"𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {html.escape(username)}\n"
                f"𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"
            )

            tags_str   = html.escape(", ".join(tags)) if tags else "N/A"
            tags_block = f"🏷 <b>Tags:</b>\n<blockquote expandable>{tags_str}</blockquote>"

            base_caption = (
                f"📺 <b>{html.escape(title)}</b>\n\n"
                f"👤 <b>Channel:</b> {html.escape(channel)}\n"
                f"👀 <b>Views:</b> {views:,}\n"
                f"👍 <b>Likes:</b> {likes:,}\n"
                f"⏳ <b>Duration:</b> {duration_str}\n"
                f"📅 <b>Published:</b> {upload_date}\n\n"
                f"{tags_block}"
                f"{footer}"
            )

            if len(base_caption) > CAPTION_LIMIT:
                allowed_tags = CAPTION_LIMIT - len(base_caption) + len(tags_str)
                tags_str = tags_str[:max(0, allowed_tags - 20)] + "…"
                tags_block = f"🏷 <b>Tags:</b>\n<blockquote expandable>{tags_str}</blockquote>"
                base_caption = (
                    f"📺 <b>{html.escape(title)}</b>\n\n"
                    f"👤 <b>Channel:</b> {html.escape(channel)}\n"
                    f"👀 <b>Views:</b> {views:,}\n"
                    f"👍 <b>Likes:</b> {likes:,}\n"
                    f"⏳ <b>Duration:</b> {duration_str}\n"
                    f"📅 <b>Published:</b> {upload_date}\n\n"
                    f"{tags_block}"
                    f"{footer}"
                )

            caption = base_caption

            markup = telebot.types.InlineKeyboardMarkup()
            if video_id:
                qualities = [
                    ("Max Res", "maxresdefault"),
                    ("High (HQ)", "hqdefault"),
                    ("Medium (MQ)", "mqdefault"),
                    ("Standard (SD)", "sddefault"),
                ]
                row = []
                for name, q in qualities:
                    t_url = f"https://img.youtube.com/vi/{video_id}/{q}.jpg"
                    row.append(telebot.types.InlineKeyboardButton(name, url=t_url))
                    if len(row) == 2:
                        markup.add(*row)
                        row = []
                if row:
                    markup.add(*row)

            sent_msg = None
            if thumb_url:
                try:
                    img_bytes = await asyncio.to_thread(
                        lambda: requests.get(thumb_url, timeout=15).content
                    )
                    thumb_file = io.BytesIO(img_bytes)
                    thumb_file.name = "thumbnail.jpg"
                    sent_msg = await bot.send_document(
                        message.chat.id, thumb_file,
                        caption=caption, parse_mode="HTML",
                        reply_markup=markup
                    )
                except Exception:
                    sent_msg = await bot.send_message(
                        message.chat.id, caption,
                        parse_mode="HTML", reply_markup=markup
                    )
            else:
                sent_msg = await bot.send_message(
                    message.chat.id, caption,
                    parse_mode="HTML", reply_markup=markup
                )

            if description:
                desc_bytes = io.BytesIO(description.encode('utf-8'))
                desc_bytes.name = f"{title[:50].strip()}_description.txt"
                await bot.send_document(
                    message.chat.id, desc_bytes,
                    caption="📝 <b>Full Description</b>",
                    parse_mode="HTML"
                )

            try:
                await bot.delete_message(message.chat.id, status_msg.message_id)
            except Exception:
                pass

        except Exception as e:
            error_msg = str(e)
            try:
                if "Forbidden" in error_msg or "403" in error_msg:
                    await bot.edit_message_text(
                        "❌ <b>Error:</b> YouTube blocked the request.",
                        chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML"
                    )
                else:
                    await bot.edit_message_text(
                        f"❌ <b>Error:</b> {html.escape(error_msg)}",
                        chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML"
                    )
            except Exception:
                await bot.send_message(
                    message.chat.id,
                    f"❌ <b>Error:</b> {html.escape(error_msg)}", parse_mode="HTML"
                )
