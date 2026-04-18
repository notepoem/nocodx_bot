import html
import config
from hashids import Hashids
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

SALT = getattr(config, 'ID_SALT', 's3cr3t_s4lt_f0r_f1l3sh4r3_b0t') 
MIN_LENGTH = getattr(config, 'MIN_LENGTH', 10)
hasher = Hashids(salt=SALT, min_length=MIN_LENGTH)

def encrypt_id(message_id: int) -> str:
    return hasher.encode(message_id)

def decrypt_id(token: str) -> int:
    try:
        decoded = hasher.decode(token)
        return decoded[0] if decoded else None
    except:
        return None

async def handle_deep_link(bot, message):
    try:
        args = message.text.split()
        if len(args) > 1:
            command_arg = args[1]
            if command_arg.startswith('file_'):
                try:
                    code_str = command_arg.split('_')[1]
                    file_message_id = decrypt_id(code_str)

                    if not file_message_id:
                        await bot.reply_to(message, "❌ Invalid or expired link.")
                        return True

                    await bot.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=config.CHANNEL_ID,
                        message_id=file_message_id
                    )
                    return True # Indicates the request was handled as a file request
                except Exception as e:
                    await bot.reply_to(message, "⚠️ Error: Could not get the file. Make sure the bot is Admin in the Storage Channel.")
                    print(f"Error retrieving file: {e}")
                    return True
    except Exception as e:
        print(f"Deep link error: {e}")
    
    return False

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("share")
    async def share_file_group(message):
        try:
            if not message.reply_to_message:
                await bot.reply_to(message, "Please reply to a file with <code>/share</code>.", parse_mode="HTML")
                return

            replied = message.reply_to_message
            
            media = (
                replied.document or 
                replied.video or 
                replied.audio or 
                replied.photo or 
                replied.voice or 
                replied.animation
            )
            
            if not media:
                await bot.reply_to(message, "Unsupported media type. I support: Document, Video, Audio, Photo, Voice, GIF.")
                return

            try:
                sent_message = await bot.copy_message(
                    chat_id=config.CHANNEL_ID,
                    from_chat_id=replied.chat.id,
                    message_id=replied.message_id
                )
            except Exception as e:
                await bot.reply_to(
                    message,
                    f"❌ <b>Setup Error:</b> I cannot save to the Storage Channel.\n\n"
                    f"Please add me as an <b>Admin</b> in Channel ID <code>{html.escape(str(config.CHANNEL_ID))}</code> so I can store files!",
                    parse_mode="HTML"
                )
                print(f"Error copying message: {e}")
                return

            encrypted_id = encrypt_id(sent_message.message_id)

            username = (await bot.get_me()).username
            link = f"https://t.me/{username}?start=file_{encrypted_id}"

            response_text = (
                f"✅ <b>File stored successfully!</b>\n\n"
                f"🔗 <b>Link:</b>\n"
                f"<code>{html.escape(link)}</code>\n\n"
                f"📥 <b>Get in Group:</b>\n"
                f"<code>/get file_{html.escape(encrypted_id)}</code>"
            )

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📥 Get File", url=link))

            await bot.reply_to(message, response_text, parse_mode="HTML", reply_markup=markup)

        except Exception as e:
            await bot.reply_to(message, f"Error: {e}")
            print(f"Error sharing file: {e}")

    @custom_command_handler("get")
    async def get_file_manual(message):
        try:
            args = message.text.split()
            if len(args) < 2:
                await bot.reply_to(message, "Usage: <code>/get file_ID</code>", parse_mode="HTML")
                return

            input_text = args[1]
            
            # Parse ID
            code_str = None
            if "start=" in input_text:
                 parts = input_text.split("start=")
                 if len(parts) > 1 and parts[-1].startswith("file_"):
                     code_str = parts[-1].split("_")[1]
            elif input_text.startswith("file_"):
                 code_str = input_text.split("_")[1]

            file_id = decrypt_id(code_str) if code_str else None
            
            if file_id:
                try:
                    await bot.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=config.CHANNEL_ID,
                        message_id=file_id 
                    )
                except Exception as e:
                    await bot.reply_to(message, "❌ Error retrieving file. Make sure I am admin in the storage channel.")
                    print(f"Error retrieving file: {e}")
            else:
                 await bot.reply_to(message, "❌ Invalid ID.")

        except Exception as e:
            await bot.reply_to(message, f"Error: {e}")
