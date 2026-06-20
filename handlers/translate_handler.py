import requests
import html
import re
import os
import uuid
import platform
import subprocess
from handlers.ocr_handler import NoteGPTService, convert_video_to_gif, CACHE_DIR
import asyncio

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None): 
    ocr_service = NoteGPTService()

    @custom_command_handler("translate", "tr", "trn")
    async def translate_handler(message):
        async def is_valid_lang(lang):
            return bool(re.match(r'^[a-z]{2,3}(-[a-z]{2,4})?$', lang, re.IGNORECASE))

        command_text_full = message.text.split(None, 1)[0].lower()
        actual_command_len = len(command_text_full)
        text_after_command = message.text[actual_command_len:].strip()
        
        target_lang = "en"
        text_to_translate = ""
        is_media = False
        media_message = None

        if message.reply_to_message:
            reply = message.reply_to_message
            
            text_to_translate = reply.text or reply.caption or ""
            has_photo = bool(reply.photo)
            has_video = bool(reply.video or reply.animation or (reply.document and reply.document.mime_type and reply.document.mime_type.startswith('video/')))

            if has_photo or has_video:
                is_media = True
                media_message = reply
                
            if text_after_command:
                possible_lang = text_after_command.split()[0].lower()
                if await is_valid_lang(possible_lang):
                    target_lang = possible_lang
        else:
            if not text_after_command:
                await bot.reply_to(message, f"❌ Usage: `{command_prefixes_list[0]}tr <lang_code> <text>` or reply to a text/media.\nExample: `{command_prefixes_list[0]}tr fr Hello!`, `{command_prefixes_list[0]}trn bn (replying to image)`", parse_mode="Markdown") 
                return
            
            parts = text_after_command.split(" ", 1)
            first_arg = parts[0].lower()
            
            if await is_valid_lang(first_arg):
                target_lang = first_arg
                text_to_translate = parts[1] if len(parts) > 1 else ""
            else:
                target_lang = "en"
                text_to_translate = text_after_command

        if is_media:
            status_msg = await bot.reply_to(message, "🔄 <b>Processing Media for Text...</b>", parse_mode="HTML")
            try:
                extracted_text = None
                
                if media_message.photo:
                    photo = media_message.photo[-1]
                    file_info = await bot.get_file(photo.file_id)
                    image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
                    extracted_text = await ocr_service.process_image(image_url, mode='ocr')

                elif media_message.video or media_message.animation or (media_message.document and media_message.document.mime_type.startswith('video/')):

                    vid_obj = media_message.video or media_message.animation or media_message.document
                    await bot.edit_message_text("⬇️ <b>Downloading Video...</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                    file_info = await bot.get_file(vid_obj.file_id)
                    downloaded_file = await bot.download_file(file_info.file_path)
                    ext = os.path.splitext(file_info.file_path)[1] or ".mp4"
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    temp_filename = os.path.join(CACHE_DIR, f"tr_temp_vid_{uuid.uuid4()}{ext}")
                    
                    try:
                        with open(temp_filename, 'wb') as new_file:
                            new_file.write(downloaded_file)
                            
                        await bot.edit_message_text("⚙️ <b>Converting to GIF...</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                        gif_path = convert_video_to_gif(temp_filename)
                        
                        if gif_path:
                            sts = ocr_service.get_sts_token_plain()
                            if sts:
                                await bot.edit_message_text("☁️ <b>Uploading to Cloud...</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                                oss_url = ocr_service.upload_file_oss(gif_path, sts, content_type='image/gif')
                                
                                if oss_url:
                                    await bot.edit_message_text("👀 <b>Extracting Text...</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                                    extracted_text = await ocr_service.process_image(oss_url, mode='ocr')
                            
                            if os.path.exists(gif_path): os.remove(gif_path)
                    
                    finally:
                        if os.path.exists(temp_filename): os.remove(temp_filename)

                if extracted_text and extracted_text.strip():
                    text_to_translate = extracted_text
                    await bot.edit_message_text("🌍 <b>Translating Extracted Text...</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                else:
                    await bot.edit_message_text("⚠️ <b>No text found in media.</b>", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                    return # Stop if no text found in media

            except Exception as e:
                await bot.edit_message_text(f"❌ <b>OCR Error:</b> {e}", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                return

        if not text_to_translate:
            await bot.reply_to(message, "❌ Please provide text to translate.", parse_mode="Markdown")
            return

        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target_lang,
                "dt": "t",
                "q": text_to_translate
            }

            resp = await asyncio.to_thread(requests.get, url, params=params)
            if resp.status_code != 200:
                await bot.reply_to(message, f"❌ Translation failed (status {resp.status_code})")
                return

            data = resp.json()

            translated = ''.join([item[0] for item in data[0] if item[0]])
            source_lang = data[2] if data[2] != data[8][0][0] else data[8][0][0]

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {html.escape(username)}"

            reply_msg = (
                f"✅ <b>𝗧𝗿𝗮𝗻𝘀𝗹𝗮𝘁𝗶𝗼𝗻 Result:</b>\n\n"
                f"{html.escape(translated)}\n\n"
                f"🌐 <i>{html.escape(source_lang.upper())} to {html.escape(target_lang.upper())}</i>"
                f"\n{footer}"
            )
            
            if is_media and 'status_msg' in locals():
                await bot.edit_message_text(reply_msg, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
            else:
                await bot.send_message(
                    message.chat.id,
                    reply_msg,
                    reply_to_message_id=message.message_id,
                    parse_mode="HTML"
                )

        except Exception as e:
            await bot.reply_to(message, f"❌ Error: {str(e)}")