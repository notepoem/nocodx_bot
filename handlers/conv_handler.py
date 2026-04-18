import asyncio
import aiohttp
import logging
import os
import ssl
import hashlib
import json
import time
import math
import uuid
import random
from telebot import types

LOGGER = logging.getLogger(__name__)

SUPPORTED_VIDEO = ["3gp", "avi", "flv", "mkv", "mov", "mp4", "ogv", "webm", "wmv"]
SUPPORTED_AUDIO = ["aac", "aiff", "alac", "amr", "flac", "m4a", "mp3", "ogg", "wav", "wma"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Apple) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]
FILE_CACHE = {}

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def get_freeconvert_headers(token=None):
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': "application/json, text/plain, */*",
        'Accept-Language': "en-US,en;q=0.9",
        'Accept-Encoding': "gzip, deflate",
        'origin': "https://www.freeconvert.com",
        'referer': "https://www.freeconvert.com/download",
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    if token:
        headers['authorization'] = f"Bearer {token}"
    return headers

async def get_guest_token(session, headers):
    url = "https://api.freeconvert.com/v1/account/guest"
    async with session.get(url, headers=headers) as resp:
        content = await resp.read()
        return content.decode('utf-8').strip()

async def create_conversion_job(session, token, input_format, output_format, headers, import_type="upload"):
    url = "https://api.freeconvert.com/v1/process/jobs"
    is_audio = output_format in ['mp3', 'aac', 'wav', 'flac', 'ogg', 'm4a', 'wma']
    
    tasks = {
        "import": {"operation": f"import/{import_type}"},
        "convert": {
            "operation": "convert",
            "input": "import",
            "input_format": input_format,
            "output_format": output_format,
            "options": {
                "audio_codec": output_format if output_format == "mp3" else "auto",
                "audio_bitrate": "192",
                "audio_frequency": "44100"
            } if is_audio else {
                "video_codec": "auto",
                "audio_codec": "auto"
            }
        },
        "export-url": {
            "operation": "export/url",
            "input": "convert"
        }
    }
    
    req_headers = headers.copy()
    req_headers['authorization'] = f"Bearer {token}"
    req_headers['Content-Type'] = "application/json"
    
    async with session.post(url, data=json.dumps({"tasks": tasks}), headers=req_headers) as resp:
        if resp.status not in [200, 201]:
            error_text = await resp.text()
            LOGGER.error(f"Error creating job: {error_text}")
            return None
        
        job_data = await resp.json()
        job_id = job_data['id']
        
        if import_type == "upload":
            task_id = job_data['tasks'][0]['id']
            upload_url = job_data['tasks'][0]['result']['form']['url']
            signature = job_data['tasks'][0]['result']['form']['parameters']['signature']
            return job_id, task_id, upload_url, signature
        return job_id

async def upload_file_chunks(session, file_content, file_name, task_id, upload_url, signature, headers):
    file_size = len(file_content)
    chunk_size = 10485760 # 10MB
    total_chunks = math.ceil(file_size / chunk_size)
    file_ext = file_name.split('.')[-1]
    identifier = f"{file_size}-{int(time.time())}-{file_name.replace('.', '')}.{file_ext}"
    
    mime_types = {
        'mp4': 'video/mp4', 'avi': 'video/x-msvideo', 'mkv': 'video/x-matroska',
        'mov': 'video/quicktime', 'wmv': 'video/x-ms-wmv', 'flv': 'video/x-flv',
        'webm': 'video/webm', 'mp3': 'audio/mpeg', 'wav': 'audio/wav',
        'flac': 'audio/flac', 'aac': 'audio/aac', 'ogg': 'audio/ogg'
    }
    mime_type = mime_types.get(file_ext.lower(), 'application/octet-stream')
    
    for chunk_num in range(1, total_chunks + 1):
        start = (chunk_num - 1) * chunk_size
        end = min(start + chunk_size, file_size)
        chunk_data = file_content[start:end]
        current_chunk_size = len(chunk_data)
        
        params = {
            'resumableChunkNumber': str(chunk_num),
            'resumableChunkSize': str(chunk_size),
            'resumableCurrentChunkSize': str(current_chunk_size),
            'resumableTotalSize': str(file_size),
            'resumableType': mime_type,
            'resumableIdentifier': identifier,
            'resumableFilename': file_name,
            'resumableRelativePath': file_name,
            'resumableTotalChunks': str(total_chunks)
        }
        
        data = aiohttp.FormData()
        for k, v in params.items():
            data.add_field(k, v)
        data.add_field('file', chunk_data, filename=f'chunk_{chunk_num}', content_type='application/octet-stream')
        
        upload_resumable_url = upload_url.replace('/api/upload/', '/api/resumable/')
        async with session.post(upload_resumable_url, params=params, data=data, headers=headers) as resp:
            await resp.read()

    join_url = upload_url.replace('/api/upload/', '/api/resumable/join/')
    join_payload = {'identifier': identifier, 'fileSize': str(file_size)}
    async with session.post(join_url, data=join_payload, headers=headers) as resp:
        await resp.read()
    
    finalize_payload = {'identifier': identifier, 'fileName': file_name, 'signature': signature}
    async with session.post(upload_url, data=finalize_payload, headers=headers) as resp:
        await resp.read()
    
    return identifier

async def check_job_status(session, job_id, token, headers):
    url = f"https://api.freeconvert.com/v1/process/jobs/{job_id}"
    req_headers = headers.copy()
    req_headers['authorization'] = f"Bearer {token}"
    
    max_retries = 60
    for _ in range(max_retries):
        async with session.get(url, headers=req_headers) as resp:
            job_data = await resp.json()
            status = job_data.get('status')
            
            if status == 'completed':
                for task in job_data.get('tasks', []):
                    if task.get('name') == 'export-url' and task.get('status') == 'completed':
                        return task.get('result', {}).get('url'), None
                return None, "Download URL not found in completed job"
            elif status in ['error', 'failed']:
                error_msg = "Conversion failed"
                for task in job_data.get('tasks', []):
                    if task.get('status') in ['error', 'failed']:
                        error_msg = task.get('message', 'Unknown error')
                        break
                return None, error_msg
            
            await asyncio.sleep(random.uniform(2.5, 4.5))
            
    return None, "Timeout waiting for conversion"

async def convert_file_api(bot, file_id: str, filename: str, target_format: str = "mp3") -> tuple:
    try:
        file_info = await bot.get_file(file_id)
        if file_info.file_size > 20 * 1024 * 1024:
            return None, "File is too large (max 20MB)."

        telegram_file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(telegram_file_url) as tg_resp:
                tg_resp.raise_for_status()
                file_content = await tg_resp.read()
            
            session_headers = get_freeconvert_headers()
            token = await get_guest_token(session, session_headers)
            input_format = filename.split('.')[-1].lower()
            
            job_res = await create_conversion_job(session, token, input_format, target_format, session_headers)
            if not job_res:
                return None, "Failed to create conversion job"
            
            job_id, task_id, upload_url, signature = job_res
            await upload_file_chunks(session, file_content, filename, task_id, upload_url, signature, session_headers)
            audio_url, error = await check_job_status(session, job_id, token, session_headers)
            
            if audio_url:
                return {
                    'success': True,
                    'url': audio_url,
                    'filename': f"converted_{filename.rsplit('.', 1)[0]}.{target_format}",
                    'format': target_format
                }, None
            else:
                return None, error or "Conversion failed"
    
    except Exception as e:
        LOGGER.error(f"Error during conversion process: {e}")
        return None, f"Error: {e}"

def get_file_cache_key(file_id, filename):
    """Generate a short unique key for the file info."""
    data = f"{file_id}_{filename}"
    key = hashlib.md5(data.encode()).hexdigest()[:8]
    FILE_CACHE[key] = {"file_id": file_id, "filename": filename}
    
    if len(FILE_CACHE) > 500:
        keys_to_remove = list(FILE_CACHE.keys())[:100]
        for k in keys_to_remove:
            FILE_CACHE.pop(k, None)
            
    return key

def create_format_keyboard(cache_key):
    markup = types.InlineKeyboardMarkup(row_width=4)
    v_btns = [types.InlineKeyboardButton(fmt.upper(), callback_data=f"cv_{fmt}_{cache_key}") for fmt in SUPPORTED_VIDEO]
    a_btns = [types.InlineKeyboardButton(fmt.upper(), callback_data=f"cv_{fmt}_{cache_key}") for fmt in SUPPORTED_AUDIO]
    
    for i in range(0, len(v_btns), 4):
        markup.add(*v_btns[i:i+4])
    for i in range(0, len(a_btns), 4):
        markup.add(*a_btns[i:i+4])
    
    return markup

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("conv", "convert")
    async def conv_handler(message):
        if check_usage_limit and not await check_usage_limit(message, "File Converter"):
            return

        replied_message = message.reply_to_message
        
        if not replied_message:
            await bot.reply_to(
                message, 
                f"❓ <b>𝗨𝘀𝗮𝗴𝗲:</b> Reply to a file with <code>{command_prefixes_list[0]}conv</code>", 
                parse_mode="HTML"
            )
            return
        
        file_obj = None
        filename = None
        
        if replied_message.video:
            file_obj = replied_message.video
            filename = file_obj.file_name or "video.mp4"
        elif replied_message.audio:
            file_obj = replied_message.audio
            filename = file_obj.file_name or "audio.mp3"
        elif replied_message.voice:
            file_obj = replied_message.voice
            filename = "voice.ogg"
        elif replied_message.document:
            file_obj = replied_message.document
            filename = file_obj.file_name or "file"
        else:
            await bot.reply_to(message, "❌ Please reply to a video, audio, or document file.")
            return

        if file_obj.file_size > 20 * 1024 * 1024:
            await bot.reply_to(message, "❌ File is too large (max 20MB).", parse_mode="HTML")
            return
        
        cache_key = get_file_cache_key(file_obj.file_id, filename)
        markup = create_format_keyboard(cache_key)
        
        await bot.reply_to(
            message,
            "📂 <b>𝗦𝗲𝗹𝗲𝗰𝘁 𝗧𝗮𝗿𝗴𝗲𝘁 𝗙𝗼𝗿𝗺𝗮𝘁:</b>\nChoose which format you want to convert to:",
            reply_markup=markup,
            parse_mode="HTML"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cv_"))
    async def callback_handler(call):
        try:
            parts = call.data.split("_")
            if len(parts) < 3: return
            
            target_format = parts[1]
            cache_key = parts[2]
            
            file_info = FILE_CACHE.get(cache_key)
            if not file_info:
                await bot.answer_callback_query(call.id, "❌ Session expired. Please try the command again.")
                return
            
            file_id = file_info["file_id"]
            filename = file_info["filename"]
            
            await bot.answer_callback_query(call.id, f"Converting to {target_format.upper()}...")
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"⚙️ 𝗖𝗼𝗻𝘃𝗲𝗿𝘁𝗶𝗻𝗴 𝗳𝗶𝗹𝗲 𝘁𝗼 <b>{target_format.upper()}</b>...",
                parse_mode="HTML"
            )
            
            result, error = await convert_file_api(bot, file_id, filename, target_format)
            
            if result and result.get('success'):
                res_url = result.get('url')
                try: await bot.delete_message(call.message.chat.id, call.message.message_id)
                except: pass
                
                user = call.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                if target_format in SUPPORTED_AUDIO:
                    await bot.send_audio(
                        chat_id=call.message.chat.id,
                        audio=res_url,
                        caption=f"✅ <b>𝗖𝗼𝗻𝘃𝗲𝗿𝘁𝗲𝗱 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>\n🎯 <b>𝗙𝗼𝗿𝗺𝗮𝘁:</b> {target_format.upper()}\n{footer}",
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_document(
                        chat_id=call.message.chat.id,
                        document=res_url,
                        caption=f"✅ <b>𝗖𝗼𝗻𝘃𝗲𝗿𝘁𝗲𝗱 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!</b>\n🎯 <b>𝗙𝗼𝗿𝗺𝗮𝘁:</b> {target_format.upper()}\n{footer}",
                        parse_mode="HTML"
                    )
            else:
                await bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"❌ <b>𝗖𝗼𝗻𝘃𝗲𝗿𝘀𝗶𝗼𝗻 𝗳𝗮𝗶𝗹𝗲𝗱:</b>\n{error}",
                    parse_mode="HTML"
                )
                
        except Exception as e:
            LOGGER.error(f"Callback conversion failed: {str(e)}")
            try: await bot.send_message(call.message.chat.id, f"❌ Conversion failed: {str(e)}")
            except: pass