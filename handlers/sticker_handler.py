import os
import system_manager
import telebot
from PIL import Image
import io
import subprocess
import zipfile
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

FFMPEG_EXE = system_manager.FFMPEG_EXE
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def process_to_webm(input_path, output_path):
    duration = 3
    target_size_bytes = 240 * 1024
    target_bitrate_kbps = int((target_size_bytes * 8) / duration / 1000)

    command = [
        FFMPEG_EXE,
        "-i", input_path,
        "-t", str(duration),
        "-vf", (
            "scale=512:512:force_original_aspect_ratio=decrease,"
            "pad=512:512:(512-iw)/2:(512-ih)/2:color=0x00000000"
        ),
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",
        "-b:v", f"{target_bitrate_kbps}k",
        "-maxrate", f"{target_bitrate_kbps}k",
        "-bufsize", f"{target_bitrate_kbps}k",
        "-deadline", "good",
        "-cpu-used", "4",
        "-an",
        "-y",
        output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def resize_image(image_data):
    im = Image.open(io.BytesIO(image_data))
    
    if im.width >= im.height:
        new_width = 512
        new_height = int(im.height * (512 / im.width))
    else:
        new_height = 512
        new_width = int(im.width * (512 / im.height))
    
    im = im.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    output_buffer = io.BytesIO()
    im.save(output_buffer, format="PNG")
    return output_buffer.getvalue()

def get_pack_name_from_arg(bot_username, user_id, arg):
    arg = arg.strip()
    
    if "t.me/addstickers/" in arg:
        return arg.split("addstickers/")[-1].split("?")[0].strip()
    
    if "_by_" in arg:
        return arg

    suffix = "".join(c for c in arg if c.isalnum() or c == "_")
    prefix = f"pack_{user_id}_"
    by_suffix = f"_by_{bot_username}"
    
    available_chars = 64 - len(prefix) - len(by_suffix)
    if available_chars < 0: # Extremely long bot username?
        available_chars = 0
        
    safe_suffix = suffix[:available_chars]
    return f"{prefix}{safe_suffix}{by_suffix}"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None, sticker_manager=None, sync_func=None):
    async def add_sticker_logic(message, pack_name, pack_title_suffix="", emojis="🌟"):
        try:
            reply = message.reply_to_message
            if not reply:
                await bot.reply_to(message, "⚠️ Please reply to a **photo, video, or GIF** to create a sticker.")
                return

            is_video = False
            media = None
            if reply.photo:
                media = reply.photo[-1]
            elif reply.video:
                media = reply.video
                is_video = True
            elif reply.animation:
                media = reply.animation
                is_video = True
            
            if not media:
                await bot.reply_to(message, "⚠️ Please reply to a **photo, video, or GIF** to create a sticker.")
                return

            if check_usage_limit and not await check_usage_limit(message, "Sticker"):
                return

            status_msg = await bot.reply_to(message, "🎨 Processing media...")
            
            file_info = await bot.get_file(media.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            user_id = message.from_user.id
            username = message.from_user.username or f"user_{user_id}"
            bot_username = (await bot.get_me()).username
            
            cache_dir = os.path.join(BASE_DIR, "cache", "sticker")
            os.makedirs(cache_dir, exist_ok=True)
            temp_in = os.path.join(cache_dir, f"temp_{user_id}_{message.message_id}_in")
            temp_out = os.path.join(cache_dir, f"temp_{user_id}_{message.message_id}_out.webm")
            
            try:
                if not is_video:
                    processed_image_data = resize_image(downloaded_file)
                    sticker_file = io.BytesIO(processed_image_data)
                    sticker_format = "static"
                else:
                    ext = ".mp4"
                    with open(temp_in + ext, 'wb') as f:
                        f.write(downloaded_file)

                    process_to_webm(temp_in + ext, temp_out)
                    with open(temp_out, 'rb') as f:
                        sticker_file = io.BytesIO(f.read())
                    sticker_format = "video"

            except Exception as e:
                print(f"Error in processing: {e}")
                err_msg = telebot.util.escape(str(e))
                await bot.edit_message_text(f"❌ Error processing media: {err_msg}", chat_id=message.chat.id, message_id=status_msg.message_id)
                return
            finally:
                for f in [temp_in + ".mp4", temp_out]:
                    if os.path.exists(f): os.remove(f)

            sticker_file.name = "sticker.png" if sticker_format == "static" else "sticker.webm"

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("➕ Add Sticker Pack", url=f"https://t.me/addstickers/{pack_name}"))

            try:

                await bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_name,
                    png_sticker=sticker_file if sticker_format == "static" else None,
                    webm_sticker=sticker_file if sticker_format == "video" else None,
                    emojis=emojis
                )
                await bot.edit_message_text(f"✅ Sticker added to <b>{pack_name}</b>!", chat_id=message.chat.id, message_id=status_msg.message_id, reply_markup=markup, parse_mode="HTML")
                
                if sticker_manager:
                    sticker_manager.add_pack(user_id, pack_name)
                    if sync_func: sync_func()
                
            except Exception as e:
                err_str = str(e).lower()
                
                if "stickerset_invalid" in err_str:
                    sticker_file.seek(0)
                    
                    full_title = f"{username}'s {pack_title_suffix} (@{bot_username})"
                    if len(full_title) > 64:
                        full_title = full_title[:61] + "..."
                    
                    try:

                        await bot.create_new_sticker_set(
                            user_id=user_id,
                            name=pack_name,
                            title=full_title,
                            png_sticker=sticker_file if sticker_format == "static" else None,
                            webm_sticker=sticker_file if sticker_format == "video" else None,
                            emojis=emojis
                        )
                        await bot.edit_message_text(f"🎉 <b>New Pack Created!</b>\nName: <code>{pack_name}</code>\n\n✅ Sticker added!", chat_id=message.chat.id, message_id=status_msg.message_id, reply_markup=markup, parse_mode="HTML")
                        
                        if sticker_manager:
                            sticker_manager.add_pack(user_id, pack_name, title=full_title)
                            if sync_func: sync_func()
                            
                    except Exception as create_e:
                        print(f"Create pack error: {create_e}")
                        err_msg = telebot.util.escape(str(create_e))
                        await bot.edit_message_text(f"❌ Error creating pack: {err_msg}", chat_id=message.chat.id, message_id=status_msg.message_id)
                else:
                    print(f"Add sticker error: {e}")
                    err_msg = telebot.util.escape(str(e))
                    await bot.edit_message_text(f"❌ Error adding sticker: {err_msg}", chat_id=message.chat.id, message_id=status_msg.message_id)
                    
        except Exception as e:
             err_msg = telebot.util.escape(str(e))
             await bot.reply_to(message, f"❌ Error: {err_msg}")

    @custom_command_handler("sticker")
    async def handle_sticker(message):
        user_id = message.from_user.id
        bot_username = (await bot.get_me()).username
        
        args = message.text.split() # Split all args
        
        target_pack = f"pack_{user_id}_by_{bot_username}" # Default
        title_suffix = "Pack"
        emojis = "🌟"
        
        if len(args) > 1:
            last_arg = args[-1]
            
            if not last_arg.isalnum() and "t.me/" not in last_arg and "pack_" not in last_arg:
                emojis = last_arg
                args = args[:-1] # Remove emoji from pack parsing
            
            if len(args) > 1:
                arg = args[1]
                if "t.me/addstickers/" in arg or "pack_" in arg or arg.replace("_","").isalnum():
                     target_pack = get_pack_name_from_arg(bot_username, user_id, arg)
                     title_suffix = f"Pack {arg}"

        await add_sticker_logic(message, target_pack, title_suffix, emojis=emojis)

    @custom_command_handler("newpack")
    async def handle_newpack(message):
        user_id = message.from_user.id
        bot_username = (await bot.get_me()).username
        
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await bot.reply_to(message, "⚠️ Usage: <code>/newpack &lt;name&gt;</code>\nExample: <code>/newpack anime</code>")
            return
            
        name_suffix = args[1]
        if not name_suffix.replace("_", "").isalnum():
             await bot.reply_to(message, "❌ Pack name can only contain letters, numbers, and underscores.")
             return
             
        target_pack = f"pack_{user_id}_{name_suffix}_by_{bot_username}"
        await add_sticker_logic(message, target_pack, f"{name_suffix} Pack")

    @custom_command_handler("packrenm", "setpacknm", "packrename")
    async def rename_pack(message):
        try:
            args = message.text.split()
            if len(args) < 3:
                await bot.reply_to(message, "⚠️ Usage: <code>/packrenm &lt;pack_name_or_link&gt; &lt;New Title&gt;</code>")
                return
            
            target_arg = args[1]
            new_title = " ".join(args[2:])
            
            if len(new_title) > 64:
                 await bot.reply_to(message, "❌ Title too long (max 64).")
                 return
                 
            user_id = message.from_user.id
            bot_username = (await bot.get_me()).username
            pack_name = get_pack_name_from_arg(bot_username, user_id, target_arg)
            
            try:
                await bot.set_sticker_set_title(pack_name, new_title)
                await bot.reply_to(message, f"✅ Pack <b>{pack_name}</b> title updated to: <b>{new_title}</b>", parse_mode="HTML")
                
                if sticker_manager:
                    if sticker_manager.rename_pack(user_id, pack_name, new_title):
                        if sync_func: sync_func()
                    else:
                        pass # Pack might not be in our DB, ignore
            except Exception as e:
                err_msg = telebot.util.escape(str(e))
                await bot.reply_to(message, f"❌ Error: {err_msg}")
                
        except Exception as e:
            print(f"Rename error: {e}")
            err_msg = telebot.util.escape(str(e))
            await bot.reply_to(message, f"❌ An internal error occurred: {err_msg}")

    @custom_command_handler("delpack", "deletepack")
    async def delete_pack_db(message):
        try:
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                await bot.reply_to(message, "⚠️ Usage: <code>/delpack &lt;pack_name_or_link&gt;</code>")
                return
            
            target = args[1]
            user_id = message.from_user.id
            bot_username = (await bot.get_me()).username
            pack_name = get_pack_name_from_arg(bot_username, user_id, target)
            
            response_lines = []
            
            telegram_deleted = False
            try:
                if await bot.delete_sticker_set(pack_name):
                    telegram_deleted = True
                    response_lines.append(f"✅ <b>Telegram:</b> Pack <code>{pack_name}</code> deleted.")
            except Exception as e:
                err_str = str(e).lower()
                if "stickerset_invalid" in err_str or "bad request: sticker set not found" in err_str:
                     response_lines.append(f"⚠️ <b>Telegram:</b> Pack not found.")
                else:
                     err_msg = telebot.util.escape(str(e))
                     response_lines.append(f"⚠️ <b>Telegram:</b> Failed to delete ({err_msg}).")

            db_deleted = False
            if sticker_manager:
                if sticker_manager.remove_pack(user_id, pack_name):
                    db_deleted = True
                    if sync_func: sync_func()
                    response_lines.append(f"✅ <b>Database:</b> Removed from list.")
                else:
                    response_lines.append(f"ℹ️ <b>Database:</b> Not found in list.")
            else:
                response_lines.append(f"⚠️ <b>Database:</b> Not available.")

            if not telegram_deleted and not db_deleted:
                final_msg = "❌ Could not delete pack from Telegram or Database.\n" + "\n".join(response_lines)
            else:
                final_msg = "\n".join(response_lines)
                
            await bot.reply_to(message, final_msg, parse_mode="HTML")
                 
        except Exception as e:
            err_msg = telebot.util.escape(str(e))
            await bot.reply_to(message, f"❌ Error: {err_msg}")

    @custom_command_handler("delsticker", "removesticker")
    async def handle_delsticker(message):
        msg = await bot.reply_to(message, "🗑️ Please **send the sticker** you want to delete from your pack.")
        await bot.register_next_step_handler(msg, process_delete_sticker)

    async def process_delete_sticker(message):
        if not message.sticker:
            await bot.reply_to(message, "❌ That's not a sticker. Process cancelled.")
            return
        
        sticker = message.sticker
        pack_name = sticker.set_name
        user_id = message.from_user.id
        bot_username = (await bot.get_me()).username

        if not pack_name or not (str(user_id) in pack_name and bot_username in pack_name):
            await bot.reply_to(message, "❌ This sticker doesn't seem to belong to one of your packs created via this bot.")
            return
            
        try:
            if await bot.delete_sticker_from_set(sticker.file_id):
                await bot.reply_to(message, f"✅ Sticker successfully deleted from pack: <code>{pack_name}</code>", parse_mode="HTML")
            else:
                await bot.reply_to(message, "❌ Failed to delete sticker.")
        except Exception as e:
            err_msg = telebot.util.escape(str(e))
            await bot.reply_to(message, f"❌ Error deleting sticker: {err_msg}")

    @custom_command_handler("pack", "packs", "mypacks")
    async def get_my_packs(message):
        user_id = message.from_user.id
        bot_username = (await bot.get_me()).username
        
        default_pack = f"pack_{user_id}_by_{bot_username}"
        text = "📂 <b>Your Sticker Packs</b>\n\n"
        
        user_packs = []
        if sticker_manager:
            user_packs = sticker_manager.get_user_packs(user_id)
            
        if user_packs:
            for i, pack in enumerate(user_packs, 1):
                name = pack['name']
                title = pack.get('title', name)
                text += f"{i}️⃣ <b>{title}</b>\n<code>https://t.me/addstickers/{name}</code>\n\n"
        else:
            try:
                await bot.get_sticker_set(default_pack)
                text += f"1️⃣ <b>Default Pack</b>\n<code>https://t.me/addstickers/{default_pack}</code>\n\n"
            except:
                text += "❌ You haven't created any packs yet."
        await bot.reply_to(message, text, parse_mode="HTML")
