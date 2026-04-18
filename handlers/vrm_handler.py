import requests
import telebot
import json
import base64
import hmac
import hashlib
import datetime
import uuid
import os
import time
import asyncio

async def get_sts_token(session):
    url = 'https://aivocal.io/api/v1/oss/sts-token'
    response = await asyncio.to_thread(session.get, url)
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 100000:
            return data['data']
        else:
            raise Exception(f"Failed to get STS token: {data['message']}")
    else:
        raise Exception(f"Failed to get STS token: HTTP {response.status_code}")

def sign_oss_request(access_key_secret, method, content_type, date_str, canonicalized_oss_headers, resource_path):
    string_to_sign = f"{method}\n\n{content_type}\n{date_str}\n{canonicalized_oss_headers}{resource_path}"
    h = hmac.new(access_key_secret.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha1)
    signature = base64.b64encode(h.digest()).decode('utf-8')
    return signature

async def upload_to_oss(sts_data, file_path, file_content=None):
    now = datetime.datetime.now(datetime.UTC)
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    file_uuid = str(uuid.uuid4())
    object_key = f"aivocal/static/audio/{year}/{month}/{day}/{file_uuid}.mp3"
    bucket_name = "nc-cdn"
    endpoint = "oss-us-west-1.aliyuncs.com"
    bucket_url = f"https://{bucket_name}.{endpoint}"
    upload_url = f"{bucket_url}/{object_key}"
    date_str = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
    content_type = 'audio/mpeg'
    canonicalized_oss_headers = f"x-oss-security-token:{sts_data['SecurityToken']}\n"
    resource_path = f"/{bucket_name}/{object_key}"
    
    signature = sign_oss_request(
        sts_data['AccessKeySecret'],
        "PUT",
        content_type,
        date_str,
        canonicalized_oss_headers,
        resource_path
    )
    
    auth_header = f"OSS {sts_data['AccessKeyId']}:{signature}"
    
    headers = {
        'Date': date_str,
        'Content-Type': content_type,
        'Authorization': auth_header,
        'x-oss-security-token': sts_data['SecurityToken'],
        'User-Agent': 'aliyun-sdk-js/6.17.1 Chrome 145.0.0.0 on Windows 10 64-bit' 
    }
    
    if file_content:
        data = file_content
    else:
        with open(file_path, 'rb') as f:
            data = f.read()
        
    response = await asyncio.to_thread(requests.put, upload_url, headers=headers, data=data)
    
    if response.status_code == 200:
        return f"https://cdn.aivocal.io/{object_key}"
    else:
        raise Exception(f"Upload failed: HTTP {response.status_code} - {response.text}")

async def initiate_separation(session, audio_url, source_name):
    url = 'https://aivocal.io/api/v1/ai-music-separation/music'
    
    payload = {
        'stem': 'vocals',
        'audio_url': audio_url,
        'source_name': source_name,
        'output_format': 'mp3',
    }
    
    post_headers = {
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://aivocal.io'
    }
    
    response = await asyncio.to_thread(session.post, url, headers=post_headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 100000:
            return data
        else:
            raise Exception(f"Separation failed: {data['message']}")
    else:
         raise Exception(f"Separation failed: HTTP {response.status_code}")

async def check_status(session, song_id):
    url = f'https://aivocal.io/api/v1/ai-music-separation/music/{song_id}'
    response = await asyncio.to_thread(session.get, url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Status check failed: HTTP {response.status_code}")

def get_progress_bar(percentage):
    completed = int(percentage / 10)
    remaining = 10 - completed
    return f"[{'█' * completed}{'░' * remaining}] {percentage}%"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    HEADERS = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
        'dnt': '1',
        'priority': 'u=1, i',
        'referer': 'https://aivocal.io/ai-vocal/remover',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
    }

    @custom_command_handler("vocal", "vrm", "remover")
    async def handle_vocal_remover(message):
        try:
            reply = message.reply_to_message
            if not reply or not (reply.audio or reply.voice or reply.document):
                await bot.reply_to(message, "⚠️ Please reply to an **audio file** or **voice message** with /vocal.")
                return

            media = reply.audio or reply.voice or reply.document
            if reply.document and not (reply.document.mime_type and reply.document.mime_type.startswith('audio/')):
                await bot.reply_to(message, "⚠️ Please reply to an **audio file**.")
                return

            if check_usage_limit and not await check_usage_limit(message, "Vocal Remover"):
                return

            status_msg = await bot.reply_to(message, "⏳ Initializing...")
            
            session = requests.Session()
            session.headers.update(HEADERS)

            async def safe_edit(text):
                try:
                    await bot.edit_message_text(text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                except Exception:
                    pass

            await safe_edit("📡 Fetching...")
            sts_data = await get_sts_token(session)

            await safe_edit("📥 Downloading audio...")
            file_info = await bot.get_file(media.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            source_name = getattr(media, 'file_name', f"audio_{message.from_user.id}.mp3") or f"audio_{message.from_user.id}.mp3"

            await safe_edit("📤 Uploading to processing server...")
            cdn_url = await upload_to_oss(sts_data, None, file_content=downloaded_file)

            await safe_edit("⚙️ Starting vocal separation...")
            result = await initiate_separation(session, cdn_url, source_name)
            
            if not result or 'data' not in result:
                await safe_edit("❌ Failed to initiate separation.")
                return

            task_data = result['data']
            song_id = task_data.get('song_id')
            if not song_id:
                await safe_edit("❌ Separation task ID not found.")
                return

            last_percentage = -1
            while True:
                status_data = await check_status(session, song_id)
                if status_data and 'data' in status_data:
                    current_status = status_data['data'].get('status')
                    percentage = status_data['data'].get('percentage', 0)
                    
                    if percentage != last_percentage:
                        progress_bar = get_progress_bar(percentage)
                        await safe_edit(f"{progress_bar}")
                        last_percentage = percentage
                    
                    if current_status == 'success':
                        vocals_url = status_data['data'].get('vocals')
                        instrumental_url = status_data['data'].get('other')
                        
                        await safe_edit("✅ <b>Separation Complete!</b>\n\n📥 Downloading results to send...")
                        
                        try:
                            media_group = []
                            if vocals_url:
                                v_res = await asyncio.to_thread(requests.get, vocals_url)
                                if v_res.status_code == 200:
                                    v_file = v_res.content
                                    media_group.append(telebot.types.InputMediaAudio(v_file, title=f"Vocals - {source_name}", performer="AI AI Vocal"))
                            
                            if instrumental_url:
                                i_res = await asyncio.to_thread(requests.get, instrumental_url)
                                if i_res.status_code == 200:
                                    i_file = i_res.content
                                    media_group.append(telebot.types.InputMediaAudio(i_file, title=f"Instrumental - {source_name}", performer="AI AI Vocal"))
                            
                            if media_group:
                                await bot.send_media_group(message.chat.id, media_group)
                                await bot.delete_message(chat_id=message.chat.id, message_id=status_msg.message_id)
                            else:
                                await safe_edit("❌ Failed to download results.")
                            
                        except Exception as delivery_error:
                            await safe_edit(f"❌ <b>Separation Complete!</b>\n\n⚠️ Failed to send as attachment: <i>{str(delivery_error)}</i>")
                            
                        break
                    elif current_status == 'failed':
                        await safe_edit("❌ Separation failed on the server.")
                        break
                
                time.sleep(5)

        except Exception as e:
            try:
                await bot.reply_to(message, f"❌ Error: {str(e)}")
            except:
                pass
