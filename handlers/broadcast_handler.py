import os
from telebot import formatting
from telebot.util import antiflood
import time
from telebot import types
import re
import asyncio

ADMIN_ID = 6785584379

def create_buttons_from_text(text):
    markup = None
    button_tags = re.findall(r'\[btn:(.+?)\|(.+?)\]', text)

    if button_tags:
        markup = types.InlineKeyboardMarkup()
        for name, url in button_tags:
            button = types.InlineKeyboardButton(text=name, url=url)
            markup.add(button)

    return markup, re.sub(r'\[btn:(.+?)\|(.+?)\]', '', text).strip()

def register(bot, custom_command_handler, COMMAND_PREFIXES, user_db, check_usage_limit=None):
    @custom_command_handler('broadcast', 'bc')
    async def broadcast_command(message):
        if ADMIN_ID == 0:
            await bot.reply_to(message, "⚠️ ADMIN_ID environment variable not set!")
            return

        if message.from_user.id != ADMIN_ID:
            await bot.reply_to(message, "❌ You are not authorized to use this command!")
            return

        replied_msg = message.reply_to_message
        
        if replied_msg and (replied_msg.photo or replied_msg.video or replied_msg.document or 
                           replied_msg.audio or replied_msg.voice or replied_msg.animation or 
                           replied_msg.sticker or replied_msg.video_note):
            all_users = user_db.get_all_users()
            total_users = len(all_users)

            if total_users == 0:
                await bot.reply_to(message, "❌ No users found in database!")
                return

            original_caption = replied_msg.caption or ""
            
            parts = message.text.split(maxsplit=1)
            custom_caption_text = parts[1] if len(parts) > 1 else original_caption
            
            reply_markup, caption = create_buttons_from_text(custom_caption_text)
            
            media_type = None
            file_id = None
            
            if replied_msg.photo:
                media_type = "photo"
                file_id = replied_msg.photo[-1].file_id
            elif replied_msg.video:
                media_type = "video"
                file_id = replied_msg.video.file_id
            elif replied_msg.document:
                media_type = "document"
                file_id = replied_msg.document.file_id
            elif replied_msg.audio:
                media_type = "audio"
                file_id = replied_msg.audio.file_id
            elif replied_msg.voice:
                media_type = "voice"
                file_id = replied_msg.voice.file_id
            elif replied_msg.animation:
                media_type = "animation"
                file_id = replied_msg.animation.file_id
            elif replied_msg.sticker:
                media_type = "sticker"
                file_id = replied_msg.sticker.file_id
            elif replied_msg.video_note:
                media_type = "video_note"
                file_id = replied_msg.video_note.file_id
            
            status_msg = await bot.reply_to(
                message, 
                f"📤 <b>𝗦𝘁𝗮𝗿𝘁𝗶𝗻𝗴 {media_type} 𝗯𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝘁𝗼 {total_users} 𝘂𝘀𝗲𝗿𝘀...</b>"
            )

            success_count = 0
            failed_count = 0
            blocked_count = 0

            for user_id, username, first_name, last_name in all_users:
                try:
                    if media_type == "photo":
                        antiflood(
                            bot.send_photo,
                            user_id,
                            file_id,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    elif media_type == "video":
                        antiflood(
                            bot.send_video,
                            user_id,
                            file_id,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    elif media_type == "document":
                        antiflood(
                            bot.send_document,
                            user_id,
                            file_id,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    elif media_type == "audio":
                        antiflood(
                            bot.send_audio,
                            user_id,
                            file_id,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    elif media_type == "voice":
                        antiflood(
                            bot.send_voice,
                            user_id,
                            file_id,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    elif media_type == "animation":
                        antiflood(
                            bot.send_animation,
                            user_id,
                            file_id,
                            caption=caption,
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
                    elif media_type == "sticker":
                        antiflood(
                            bot.send_sticker,
                            user_id,
                            file_id,
                            reply_markup=reply_markup
                        )
                    elif media_type == "video_note":
                        antiflood(
                            bot.send_video_note,
                            user_id,
                            file_id,
                            reply_markup=reply_markup
                        )
                    
                    success_count += 1

                    if success_count % 10 == 0:
                        try:
                            await bot.edit_message_text(
                                f"📤 <b>𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁𝗶𝗻𝗴 {media_type}...</b>\n\n"
                                f"✅ <b>𝗦𝗲𝗻𝘁:</b> {success_count}\n"
                                f"❌ <b>𝗙𝗮𝗶𝗹𝗲𝗱:</b> {failed_count}\n"
                                f"🚫 <b>𝗕𝗹𝗼𝗰𝗸𝗲𝗱:</b> {blocked_count}\n"
                                f"📊 <b>𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:</b> {success_count + failed_count + blocked_count}/{total_users}",
                                status_msg.chat.id,
                                status_msg.message_id
                            )
                        except:
                            pass

                except Exception as e:
                    error_str = str(e).lower()
                    if 'blocked' in error_str or 'bot was blocked' in error_str:
                        blocked_count += 1
                    else:
                        failed_count += 1

                time.sleep(0.05)

            user = message.from_user
            username_footer = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username_footer}"

            final_report = (
                f"📊 <b>{media_type.upper()} 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲!</b>\n\n"
                f"✅ <b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝘀𝗲𝗻𝘁:</b> <b>{success_count}</b>\n"
                f"🚫 <b>𝗕𝗹𝗼𝗰𝗸𝗲𝗱 𝗯𝘆 𝘂𝘀𝗲𝗿:</b> <b>{blocked_count}</b>\n"
                f"❌ <b>𝗙𝗮𝗶𝗹𝗲𝗱:</b> <b>{failed_count}</b>\n"
                f"📈 <b>𝗧𝗼𝘁𝗮𝗹 𝘂𝘀𝗲𝗿𝘀:</b> <b>{total_users}</b>\n\n"
                f"<b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀 𝗿𝗮𝘁𝗲:</b> <b>{(success_count/total_users*100):.1f}%</b>"
                f"\n{footer}"
            )

            await bot.edit_message_text(
                final_report,
                status_msg.chat.id,
                status_msg.message_id,
                parse_mode='HTML'
            )
            return

        parts = message.text.split(maxsplit=2)

        if len(parts) < 3:
            help_text = formatting.format_text(
                formatting.hbold("📢 Broadcast Command Usage"),
                "",
                formatting.hbold("Text Broadcast:"),
                formatting.hcode("/broadcast <mode> <message>"),
                "",
                formatting.hbold("Modes:"),
                "• " + formatting.hcode("html") + " - Send with HTML formatting",
                "• " + formatting.hcode("text") + " - Send as plain text",
                "",
                formatting.hbold("Media Broadcast:"),
                "• Reply to any media (photo/video/audio/document/animation/voice/sticker) with:",
                "  " + formatting.hcode("/broadcast") + " - Uses original caption",
                "  " + formatting.hcode("/broadcast <custom caption>") + " - Uses custom caption with formatting",
                "",
                formatting.hbold("Supported Media Types:"),
                "• 📷 Photo",
                "• 🎥 Video",
                "• 📄 Document (PDF, files, etc)",
                "• 🎵 Audio",
                "• 🎤 Voice",
                "• 🎬 Animation (GIF)",
                "• 😀 Sticker",
                "• ⭕ Video Note",
                "",
                formatting.hbold("Button Tag:"),
                "• Use " + formatting.hcode("[btn:Button Name|URL]") + " to add buttons.",
                "• Example: " + formatting.hcode("[btn:Visit Google|https://google.com]"),
                separator="\n"
            )
            await bot.reply_to(message, help_text, parse_mode='HTML')
            return

        mode = parts[1].lower()
        broadcast_message_with_tags = parts[2]

        if mode not in ['html', 'text']:
            await bot.reply_to(message, "❌ Invalid mode! Use 'html' or 'text'")
            return

        reply_markup, broadcast_message = create_buttons_from_text(broadcast_message_with_tags)

        all_users = user_db.get_all_users()
        total_users = len(all_users)

        if total_users == 0:
            await bot.reply_to(message, "❌ No users found in database!")
            return

        status_msg = await bot.reply_to(
            message, 
            f"📤 <b>𝗦𝘁𝗮𝗿𝘁𝗶𝗻𝗴 𝗯𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝘁𝗼 {total_users} 𝘂𝘀𝗲𝗿𝘀...</b>\n\n<b>𝗠𝗼𝗱𝗲:</b> {mode.upper()}"
        )

        success_count = 0
        failed_count = 0
        blocked_count = 0

        parse_mode = 'HTML' if mode == 'html' else None

        for user_id, username, first_name, last_name in all_users:
            try:
                antiflood(
                    bot.send_message,
                    user_id,
                    broadcast_message,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                success_count += 1

                if success_count % 10 == 0:
                    try:
                        await bot.edit_message_text(
                            f"📤 <b>𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁𝗶𝗻𝗴...</b>\n\n"
                            f"✅ <b>𝗦𝗲𝗻𝘁:</b> {success_count}\n"
                            f"❌ <b>𝗙𝗮𝗶𝗹𝗲𝗱:</b> {failed_count}\n"
                            f"🚫 <b>𝗕𝗹𝗼𝗰𝗸𝗲𝗱:</b> {blocked_count}\n"
                            f"📊 <b>𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:</b> {success_count + failed_count + blocked_count}/{total_users}",
                            status_msg.chat.id,
                            status_msg.message_id
                        )
                    except:
                        pass

            except Exception as e:
                error_str = str(e).lower()
                if 'blocked' in error_str or 'bot was blocked' in error_str:
                    blocked_count += 1
                else:
                    failed_count += 1

            time.sleep(0.05)

        user = message.from_user
        username_footer = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username_footer}"

        final_report = (
            f"📊 <b>𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲!</b>\n\n"
            f"✅ <b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝘀𝗲𝗻𝘁:</b> <b>{success_count}</b>\n"
            f"🚫 <b>𝗕𝗹𝗼𝗰𝗸𝗲𝗱 𝗯𝘆 𝘂𝘀𝗲𝗿:</b> <b>{blocked_count}</b>\n"
            f"❌ <b>𝗙𝗮𝗶𝗹𝗲𝗱:</b> <b>{failed_count}</b>\n"
            f"📈 <b>𝗧𝗼𝘁𝗮𝗹 𝘂𝘀𝗲𝗿𝘀:</b> <b>{total_users}</b>\n\n"
            f"<b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀 𝗿𝗮𝘁𝗲:</b> <b>{(success_count/total_users*100):.1f}%</b>"
            f"\n{footer}"
        )

        await bot.edit_message_text(
            final_report,
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode='HTML'
        )

    @custom_command_handler('stats', 'userstats')
    async def stats_command(message):
        if ADMIN_ID == 0 or message.from_user.id != ADMIN_ID:
            return

        total_users = user_db.get_user_count()
        all_users = user_db.get_all_users()

        users_with_username = sum(1 for u in all_users if u[1] is not None)
        users_without_username = total_users - users_with_username

        user = message.from_user
        username_footer = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username_footer}"

        stats_text = (
            f"📊 <b>𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝗶𝘀𝘁𝗶𝗰𝘀</b>\n\n"
            f"👥 <b>𝗧𝗼𝘁𝗮𝗹 𝗨𝘀𝗲𝗿𝘀:</b> <b>{total_users}</b>\n"
            f"✅ <b>𝗪𝗶𝘁𝗵 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲:</b> <b>{users_with_username}</b>\n"
            f"❌ <b>𝗪𝗶𝘁𝗵𝗼𝘂𝘁 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲:</b> <b>{users_without_username}</b>"
            f"\n{footer}"
        )

        await bot.reply_to(message, stats_text, parse_mode='HTML')

    @custom_command_handler('getusers', 'downloadusers', 'usersfile')
    async def get_users_file(message):
        if ADMIN_ID == 0:
            await bot.reply_to(message, "⚠️ ADMIN_ID environment variable not set!")
            return

        if message.from_user.id != ADMIN_ID:
            await bot.reply_to(message, "❌ You are not authorized to use this command!")
            return

        try:
            json_content = user_db.get_json_content_safely()
            total_users = user_db.get_user_count()

            from io import BytesIO
            json_bytes = BytesIO(json_content.encode('utf-8'))
            json_bytes.name = 'bot_users.json'

            await bot.send_document(
                message.chat.id,
                json_bytes,
                caption=formatting.format_text(
                    formatting.hbold("📁 User Database File"),
                    "",
                    f"👥 Total Users: {formatting.hbold(str(total_users))}",
                    f"📅 Downloaded: {formatting.hcode(time.strftime('%Y-%m-%d %H:%M:%S'))}",
                    separator="\n"
                ),
                parse_mode='HTML'
            )
        except Exception as e:
            await bot.reply_to(message, f"❌ Error sending file: {str(e)}")
