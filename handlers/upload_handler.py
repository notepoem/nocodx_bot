import asyncio
import aiohttp
import logging
import mimetypes
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

LOGGER = logging.getLogger(__name__)

async def _try_catbox(session: aiohttp.ClientSession, file_content: bytes, filename: str) -> str | None:
    """Upload to catbox.moe; return URL or None."""
    form_data = aiohttp.FormData()
    form_data.add_field('reqtype', 'fileupload')
    form_data.add_field('fileToUpload', file_content, filename=filename,
                        content_type='application/octet-stream')
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        async with session.post("https://catbox.moe/user/api.php",
                                data=form_data, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status in (200, 201):
                text = (await resp.text()).strip()
                if text.startswith("http"):
                    return text
                LOGGER.warning(f"Catbox unexpected response: {text[:200]!r}")
    except Exception as e:
        LOGGER.warning(f"Catbox upload failed: {e}")
    return None


async def _try_0x0(session: aiohttp.ClientSession, file_content: bytes, filename: str) -> str | None:
    """Fallback upload to 0x0.st; return URL or None."""
    form_data = aiohttp.FormData()
    form_data.add_field('file', file_content, filename=filename,
                        content_type='application/octet-stream')
    try:
        async with session.post("https://0x0.st",
                                data=form_data, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status in (200, 201):
                text = (await resp.text()).strip()
                if text.startswith("http"):
                    return text
                LOGGER.warning(f"0x0.st unexpected response: {text[:200]!r}")
    except Exception as e:
        LOGGER.warning(f"0x0.st upload failed: {e}")
    return None


async def upload_file_advanced(bot, file_id: str, filename: str) -> tuple:
    try:
        file_info = await bot.get_file(file_id)
        telegram_file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

        LOGGER.info(f"Downloading file ({file_info.file_size} bytes) from Telegram.")

        async with aiohttp.ClientSession() as session:
            async with session.get(telegram_file_url, timeout=aiohttp.ClientTimeout(total=60)) as tg_resp:
                tg_resp.raise_for_status()
                file_content = await tg_resp.read()

            LOGGER.info("Downloaded. Trying Catbox.moe…")
            url = await _try_catbox(session, file_content, filename)

            if not url:
                LOGGER.info("Catbox failed. Trying 0x0.st fallback…")
                url = await _try_0x0(session, file_content, filename)

            if url:
                LOGGER.info(f"Upload successful: {url}")
                return url, None
            return None, "Both Catbox.moe and 0x0.st failed to upload the file."

    except aiohttp.ClientError as e:
        LOGGER.error(f"Network error during upload: {e}")
        return None, f"Network error: {e}"
    except Exception as e:
        LOGGER.error(f"Upload error: {e}")
        return None, f"Upload error: {e}"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("upload")
    async def upload_handler(message):
        replied_message = message.reply_to_message

        if not replied_message:
            await bot.reply_to(message, "⚠️ <b>Please reply to a file to upload it.</b>", parse_mode="HTML")
            return

        file_obj = None
        filename = None

        if replied_message.photo:
            file_obj = replied_message.photo[-1]
            filename = "photo.jpg"
        elif replied_message.video:
            file_obj = replied_message.video
            filename = file_obj.file_name or "video.mp4"
        elif replied_message.audio:
            file_obj = replied_message.audio
            filename = file_obj.file_name or "audio.mp3"
        elif replied_message.voice:
            file_obj = replied_message.voice
            filename = "voice.ogg"
        elif replied_message.animation:
            file_obj = replied_message.animation
            filename = file_obj.file_name or "animation.mp4"
        elif replied_message.video_note:
            file_obj = replied_message.video_note
            filename = "video_note.mp4"
        elif replied_message.sticker:
            file_obj = replied_message.sticker
            if file_obj.is_animated: filename = "sticker.tgs"
            elif file_obj.is_video: filename = "sticker.webm"
            else: filename = "sticker.webp"
        elif replied_message.document:
            file_obj = replied_message.document
            filename = file_obj.file_name or "document"
            if '.' not in filename:
                ext = mimetypes.guess_extension(file_obj.mime_type) if file_obj.mime_type else ".txt"
                filename += (ext or ".txt")
        else:
            await bot.reply_to(message, "❌ <b>Unsupported file type.</b>", parse_mode="HTML")
            return

        if file_obj.file_size > 20 * 1024 * 1024:
            await bot.reply_to(
                message, 
                "❌ <b>Sorry, the file size is too large. The maximum supported size is 20 MB.</b>", 
                parse_mode="HTML"
            )
            return

        loading_message = await bot.reply_to(message, "**Uploading your file...**", parse_mode="Markdown")

        try:
            file_id = file_obj.file_id

            uploaded_url, error = await upload_file_advanced(bot, file_id, filename)

            if uploaded_url:
                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                formatted_url = (
                    f"✅ <b>𝗙𝗶𝗹𝗲 𝘂𝗽𝗹𝗼𝗮𝗱𝗲𝗱 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>\n\n"
                    f"🔗 <b>𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗟𝗶𝗻𝗸:</b>\n<code>{uploaded_url}</code>\n\n"
                    f"🕒 <i>Files are hosted on a highly stable and permanent server.</i>\n{footer}"
                )
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("⬇️ Download", url=uploaded_url))

                await bot.edit_message_text(
                    chat_id=loading_message.chat.id,
                    message_id=loading_message.id,
                    text=formatted_url,
                    parse_mode="HTML",
                    reply_markup=markup
                )
            else:
                error_message = f"Sorry, file upload failed. Error: {error}"
                await bot.edit_message_text(
                    chat_id=loading_message.chat.id,
                    message_id=loading_message.id,
                    text=error_message,
                )
                if error:
                    LOGGER.error(f"Upload error: {error}")

        except Exception as e:
            LOGGER.error(f"Upload process failed. Error: {str(e)}")
            await bot.edit_message_text(
                chat_id=loading_message.chat.id,
                message_id=loading_message.id,
                text=f"**Sorry, file upload failed. Error: {str(e)}**",
                parse_mode="Markdown"
            )