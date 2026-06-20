import base64
import io
import os
import telebot
from PIL import Image
import asyncio

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    
    async def send_large_text(chat_id, text, filename="output.txt", caption=""):
        if len(text) <= 4000:
            msg = f"{caption}\n<code>{text}</code>" if caption else text
            await bot.send_message(chat_id, msg, parse_mode="HTML")
        else:
            with io.BytesIO(text.encode('utf-8')) as f:
                f.name = filename
                await bot.send_document(chat_id, f, caption=f"{caption} (Sent as file due to length)")

    @custom_command_handler("b64", "b64e", "base64")
    async def handle_encode(message):
        if check_usage_limit and not await check_usage_limit(message, "Base64"):
            return

        target_text = ""
        is_binary = False
        file_data = None
        
        if message.reply_to_message:
            reply = message.reply_to_message
            if reply.text:
                target_text = reply.text
            elif reply.document or reply.photo or reply.audio or reply.voice or reply.video:
                is_binary = True
                status = await bot.reply_to(message, "⬇️ Downloading media for encoding...")
                try:
                    if reply.photo: file_id = reply.photo[-1].file_id
                    elif reply.document: file_id = reply.document.file_id
                    elif reply.audio: file_id = reply.audio.file_id
                    elif reply.voice: file_id = reply.voice.file_id
                    elif reply.video: file_id = reply.video.file_id
                    
                    file_info = await bot.get_file(file_id)
                    file_data = await bot.download_file(file_info.file_path)
                    
                    if reply.document and reply.document.mime_type and reply.document.mime_type.startswith('text/'):
                        try:
                            target_text = file_data.decode('utf-8')
                            is_binary = False
                        except:
                            pass

                    await bot.delete_message(message.chat.id, status.message_id)
                except Exception as e:
                    await bot.edit_message_text(f"❌ Failed to download: {e}", chat_id=message.chat.id, message_id=status.message_id)
                    return
        
        if not target_text and not is_binary:
            args = message.text.split(maxsplit=1)
            if len(args) > 1:
                target_text = args[1]
            else:
                await bot.reply_to(message, "⚠️ Usage: `/b64encode <text>` or reply to text/file.")
                return

        try:
            if is_binary and file_data:
                encoded_str = base64.b64encode(file_data).decode('utf-8')
                await send_large_text(message.chat.id, encoded_str, "base64_encoded.txt", "✅ <b>Encoded binary to Base64:</b>")
            else:
                encoded_str = base64.b64encode(target_text.encode('utf-8')).decode('utf-8')
                await send_large_text(message.chat.id, encoded_str, "base64_encoded.txt", "✅ <b>Encoded text to Base64:</b>")
                
        except Exception as e:
            await bot.reply_to(message, f"❌ Encoding Error: {e}")


    @custom_command_handler("b64decode", "b64d")
    async def handle_decode(message):
        if check_usage_limit and not await check_usage_limit(message, "Base64"):
            return

        target_b64 = ""
        
        if message.reply_to_message:
            reply = message.reply_to_message
            if reply.text:
                target_b64 = reply.text
            elif reply.document and reply.document.mime_type and reply.document.mime_type.startswith('text/'):
                try:
                    status = await bot.reply_to(message, "⬇️ Downloading file for decoding...")
                    file_info = await bot.get_file(reply.document.file_id)
                    file_data = await bot.download_file(file_info.file_path)
                    target_b64 = file_data.decode('utf-8')
                    await bot.delete_message(message.chat.id, status.message_id)
                except Exception as e:
                    await bot.reply_to(message, f"❌ Failed to read file: {e}")
                    return
        
        if not target_b64:
            args = message.text.split(maxsplit=1)
            if len(args) > 1:
                target_b64 = args[1]
            else:
                await bot.reply_to(message, "⚠️ Usage: `/b64decode <base64_string>` or reply to text/file.")
                return
        
        target_b64 = target_b64.strip()
        
        if target_b64.startswith("data:"):
            if ";base64," in target_b64:
                target_b64 = target_b64.split(";base64,")[-1]
        
        target_b64 = target_b64.replace("\n", "").replace(" ", "").replace("\r", "")

        try:
            decoded_bytes = base64.b64decode(target_b64)
            
            # 3. Media Detection Logic
            # --- Image Detection ---
            try:
                with io.BytesIO(decoded_bytes) as img_check:
                    img = Image.open(img_check)
                    img_format = img.format.lower() if img.format else "png"
                    img_io = io.BytesIO(decoded_bytes)
                    img_io.name = f"decoded_image.{img_format}"
                    await bot.send_photo(message.chat.id, img_io, caption=f"🖼 <b>Decoded {img.format} Image</b>", parse_mode="HTML")
                    return
            except:
                pass

            # --- Audio Detection (Magic Numbers) ---
            audio_ext = None
            if decoded_bytes.startswith(b'ID3') or decoded_bytes.startswith(b'\xff\xfb'): audio_ext = "mp3"
            elif decoded_bytes.startswith(b'OggS'): audio_ext = "ogg"
            elif decoded_bytes.startswith(b'RIFF') and b'WAVE' in decoded_bytes[:15]: audio_ext = "wav"
            elif decoded_bytes.startswith(b'\x00\x00\x00\x1cftypM4A'): audio_ext = "m4a"
            elif decoded_bytes.startswith(b'fLaC'): audio_ext = "flac"

            if audio_ext:
                audio_io = io.BytesIO(decoded_bytes)
                audio_io.name = f"decoded_audio.{audio_ext}"
                await bot.send_audio(message.chat.id, audio_io, caption=f"🎵 <b>Decoded {audio_ext.upper()} Audio</b>", parse_mode="HTML")
                return

            # --- Document Detection (Magic Numbers) ---
            doc_info = None
            if decoded_bytes.startswith(b'%PDF'): doc_info = ("pdf", "📄 <b>Decoded PDF Document</b>")
            elif decoded_bytes.startswith(b'PK\x03\x04'): doc_info = ("zip", "📦 <b>Decoded ZIP Archive</b>")
            elif decoded_bytes.startswith(b'\x1aE\xdf\xa3'): doc_info = ("mkv", "🎬 <b>Decoded Video (MKV)</b>")
            elif decoded_bytes.startswith(b'\x00\x00\x00\x18ftypmp42') or decoded_bytes.startswith(b'\x00\x00\x00\x20ftypisom'): doc_info = ("mp4", "🎬 <b>Decoded Video (MP4)</b>")

            if doc_info:
                ext, capt = doc_info
                doc_io = io.BytesIO(decoded_bytes)
                doc_io.name = f"decoded.{ext}"
                await bot.send_document(message.chat.id, doc_io, caption=capt, parse_mode="HTML")
                return

            try:
                decoded_text = decoded_bytes.decode('utf-8')
                await send_large_text(message.chat.id, decoded_text, "decoded_text.txt", "✅ <b>Decoded Text:</b>")
            except UnicodeDecodeError:
                file_io = io.BytesIO(decoded_bytes)
                file_io.name = "decoded_file.bin"
                await bot.send_document(message.chat.id, file_io, caption="📁 <b>Decoded Binary File</b> (Unknown format)", parse_mode="HTML")
                
        except Exception as e:
            await bot.reply_to(message, f"❌ Decoding Error: {e}")
