import os
import asyncio
import aiohttp
import aiofiles
import time
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from langdetect import detect, DetectorFactory
from urllib.parse import quote

DetectorFactory.seed = 0  

async def download_file(url, path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            if resp.status == 200:
                f = await aiofiles.open(path, mode='wb')
                await f.write(await resp.read())
                await f.close()
            else:
                raise Exception(f"Failed to download file: HTTP {resp.status}")

tts_cache = {}
TTS_CACHE_EXPIRY = 600

def clean_expired_cache():
    current_time = time.time()
    expired_keys = [k for k, v in tts_cache.items() if current_time - v.get('timestamp', 0) > TTS_CACHE_EXPIRY]
    for key in expired_keys:
        del tts_cache[key]

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None): 
    @custom_command_handler("say")
    async def handle_say2(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "Say"):
            return

        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             text_to_say = " ".join(parts_split[1:]).strip()
        else:
             text_to_say = ""

        if not text_to_say:
            await bot.reply_to(message, f"❌ Text missing! Usage: `{command_prefixes_list[0]}say your text`\nExample: `{command_prefixes_list[1]}say Hello World`", parse_mode="Markdown") 
            return

        content = text_to_say

        try:
            lang_code = detect(content)
        except:
            lang_code = "en"

        allowed_langs = ["ru", "en", "ko", "ja", "tl", "bn", "si", "fr", "de", "es"]

        if lang_code not in allowed_langs:
            lang_code = "en"

        clean_expired_cache()
        
        cache_key = f"{message.chat.id}_{message.message_id}"
        tts_cache[cache_key] = {
            'content': content,
            'lang_code': lang_code,
            'timestamp': time.time()
        }

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🌐 Google", callback_data=f"tts_google_{cache_key}"),
            InlineKeyboardButton("🤖 OpenAI", callback_data=f"tts_openai_{cache_key}")
        )

        await bot.reply_to(message, f"🎤 <b>Select 𝗧𝗲𝗫𝘁-𝘁𝗼-𝗦𝗽𝗲𝗲𝗰𝗵 𝗣𝗿𝗼𝘃𝗶𝗱𝗲𝗿:</b>\n{footer}", parse_mode="HTML", reply_markup=keyboard)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tts_') and not call.data.startswith('tts_voice_'))
    async def handle_tts_callback(call):
        data_parts = call.data.split('_')
        
        if len(data_parts) < 3:
            await bot.answer_callback_query(call.id, "❌ Invalid callback data")
            return

        provider = data_parts[1]
        cache_key = '_'.join(data_parts[2:])

        if cache_key not in tts_cache:
            await bot.answer_callback_query(call.id, "❌ Session expired, please try again.")
            return
        
        current_time = time.time()
        if current_time - tts_cache[cache_key].get('timestamp', 0) > TTS_CACHE_EXPIRY:
            del tts_cache[cache_key]
            await bot.answer_callback_query(call.id, "❌ Session expired, please try again.")
            return

        tts_cache[cache_key]['timestamp'] = time.time()

        cached_data = tts_cache[cache_key]
        content = cached_data['content']
        lang_code = cached_data['lang_code']

        if provider == 'google':
            
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⏳ Generating voice using Google TTS..."
            )

            async def process_google():
                try:
                    cache_dir = os.path.join(os.getcwd(), "cache", "say")
                    os.makedirs(cache_dir, exist_ok=True)
                    filename = f"tts_{call.message.chat.id}_{call.message.message_id}.mp3"
                    filepath = os.path.join(cache_dir, filename)

                    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={quote(content)}&tl={lang_code}&client=tw-ob"

                    await download_file(tts_url, filepath)

                    with open(filepath, "rb") as voice:
                        await bot.send_voice(call.message.chat.id, voice, reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None)

                    os.remove(filepath)
                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                    
                    if cache_key in tts_cache:
                        del tts_cache[cache_key]

                except Exception as e:
                    await bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"❌ Error occurred: {str(e)}"
                    )

            await process_google()
            await bot.answer_callback_query(call.id)

        elif provider == 'openai':
            voices = ['alloy', 'echo', 'fable', 'nova', 'onyx', 'shimmer', 'coral', 'ash', 'ballad', 'sage']
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            buttons = [InlineKeyboardButton(f"🎵 {voice.title()}", callback_data=f"tts_voice_{voice}_{cache_key}") for voice in voices]
            for i in range(0, len(buttons), 2):
                if i + 1 < len(buttons):
                    keyboard.add(buttons[i], buttons[i+1])
                else:
                    keyboard.add(buttons[i])

            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🎤 <b>Select OpenAI Voice Model:</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tts_voice_'))
    async def handle_voice_callback(call):
        data_parts = call.data.split('_')
        if len(data_parts) < 4:
            await bot.answer_callback_query(call.id, "❌ Invalid callback data")
            return
        voice = data_parts[2]
        cache_key = '_'.join(data_parts[3:])

        if cache_key not in tts_cache:
            await bot.answer_callback_query(call.id, "❌ Session expired, please try again.")
            return
        
        current_time = time.time()
        if current_time - tts_cache[cache_key].get('timestamp', 0) > TTS_CACHE_EXPIRY:
            del tts_cache[cache_key]
            await bot.answer_callback_query(call.id, "❌ Session expired, please try again.")
            return

        tts_cache[cache_key]['timestamp'] = time.time()

        cached_data = tts_cache[cache_key]
        content = cached_data['content']

        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"⏳ Generating voice using OpenAI TTS ({voice})..."
        )

        async def process_openai():
            try:
                cache_dir = os.path.join(os.getcwd(), "cache", "say")
                os.makedirs(cache_dir, exist_ok=True)
                filename = f"tts_{call.message.chat.id}_{call.message.message_id}.mp3"
                filepath = os.path.join(cache_dir, filename)

                tts_url = f"https://tts-api-rho.vercel.app/generate-speech?input={quote(content)}&voice={voice}&response_format=mp3"

                await download_file(tts_url, filepath)

                with open(filepath, "rb") as voice_file:
                    await bot.send_voice(call.message.chat.id, voice_file, reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None)

                os.remove(filepath)
                await bot.delete_message(call.message.chat.id, call.message.message_id)
                
                if cache_key in tts_cache:
                    del tts_cache[cache_key]

            except Exception as e:
                await bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"❌ Error occurred: {str(e)}"
                )

        await process_openai()
        await bot.answer_callback_query(call.id)
