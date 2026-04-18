import os
import requests
import time
import io
import threading
import logging
import hashlib
import uuid
import html
import random
import asyncio

# --- GLOBAL LIMITS ---
user_daily_limits = {}
daily_limits_lock = threading.Lock()

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# List of realistic Browser User-Agents and their corresponding sec-ch-ua
USER_AGENTS = [
    {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-platform': '"Windows"'
    },
    {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="142", "Chromium";v="142", "Not A(Brand";v="24"',
        'sec-ch-ua-platform': '"macOS"'
    },
    {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="141", "Chromium";v="141", "Not A(Brand";v="24"',
        'sec-ch-ua-platform': '"Linux"'
    },
    {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'sec-ch-ua': '', # Firefox doesn't usually send sec-ch-ua
        'sec-ch-ua-platform': '"Windows"'
    },
    {
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
        'sec-ch-ua': '',
        'sec-ch-ua-platform': '"iOS"'
    }
]

def generate_dynamic_api_user():
    unique_id = str(uuid.uuid4())
    hash_code = hashlib.md5(unique_id.encode()).hexdigest()
    
    code_num = int(hash_code[:6], 16) % 1000
    product_code = f"0{67000 + code_num}"[-6:]
    
    product_serial = hashlib.sha256(unique_id.encode()).hexdigest()[:32]
    
    return {
        'product-code': product_code,
        'product-serial': product_serial
    }

def get_headers():
    api_user = generate_dynamic_api_user()
    ua_data = random.choice(USER_AGENTS)
    
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
        'origin': 'https://remaker.ai',
        'product-code': api_user['product-code'],
        'product-serial': api_user['product-serial'],
        'referer': 'https://remaker.ai/',
        'user-agent': ua_data['user-agent'],
        'sec-ch-ua-mobile': '?1' if 'Mobile' in ua_data['user-agent'] else '?0',
    }
    
    if ua_data['sec-ch-ua']:
        headers['sec-ch-ua'] = ua_data['sec-ch-ua']
    
    if ua_data['sec-ch-ua-platform']:
        headers['sec-ch-ua-platform'] = ua_data['sec-ch-ua-platform']
        
    return headers

HEADERS = get_headers()

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    async def check_status_and_send(job_id, chat_id, message_id, user_id, username, is_compressed=False):
        max_attempts = 40
        attempts = 0

        while attempts < max_attempts:
            try:
                response = await asyncio.to_thread(requests.get, 
                    f'https://api.remaker.ai/api/pai/v4/ai-enhance/get-job/{job_id}',
                    headers=get_headers(),
                    timeout=15
                )
                data = response.json()

                if data.get('code') == 100000:
                    result = data.get('result', {})
                    output_urls = result.get('output', [])
                    if output_urls:
                        original_link = output_urls[0]
                        img_res = await asyncio.to_thread(requests.get, original_link, timeout=30)
                        img_data = img_res.content

                        file_size_mb = len(img_data) / (1024 * 1024)

                        file_stream = io.BytesIO(img_data)
                        file_stream.name = f"Enhanced_{job_id}.png"

                        with daily_limits_lock:
                            if user_id in user_daily_limits:
                                user_daily_limits[user_id] -= 1
                            else:
                                user_daily_limits[user_id] = 9 # Start from 10, now at 9
                            remaining = user_daily_limits[user_id]

                        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                        note = ""
                        if is_compressed:
                            note = ("⚠️ <b>Note:</b> Telegram compressed your input photo.\n"
                                    "📌 Send as <b>File/Document</b> for best results.\n\n")
                        else:
                            note = "✅ Original quality preserved!\n\n"

                        caption_text = (
                            "✨ <b>Image Enhanced Successfully</b>\n\n"
                            f"{note}"
                            f"📦 <b>𝗢𝘂𝘁𝗽𝘂𝘁 𝗦𝗶𝘇𝗲:</b> {file_size_mb:.2f} MB\n"
                            f"⚡ <b>𝗥𝗲𝗺𝗮𝗶𝗻𝗶𝗻𝗴:</b> {remaining}\n"
                            f"🔗 <a href='{original_link}'>𝗗𝗶𝗿𝗲𝗰𝘁 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗟𝗶𝗻𝗸</a>\n"
                            f"\n{footer}"
                        )

                        await bot.send_document(
                            chat_id,
                            file_stream,
                            caption=caption_text,
                            parse_mode="HTML",
                            reply_to_message_id=message_id
                        )
                        return True
                elif data.get('code') in [300013, 201, 202]: # Common processing codes
                    time.sleep(4)
                else:
                    print(f"[ENH] Unexpected code: {data.get('code')}")
                    return False
            except Exception as e:
                print(f"[ENH] Status check error: {str(e)}")
                pass

            attempts += 1
        return False

    @custom_command_handler("enh")
    async def enh_handler(message):
        if check_usage_limit and not await check_usage_limit(message, "Enh"):
            return

        user_id = message.from_user.id
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)

        with daily_limits_lock:
            if user_id not in user_daily_limits:
                user_daily_limits[user_id] = 10
            if user_daily_limits[user_id] <= 0:
                await bot.reply_to(message, "❌ <b>Daily limit reached (10/10).</b>", parse_mode="HTML")
                return

        if not message.reply_to_message:
            await bot.reply_to(message, "⚠️ Reply to a photo or image file with `/enh`.")
            return

        has_photo = message.reply_to_message.photo
        has_document = message.reply_to_message.document

        if not has_photo and not (has_document and has_document.mime_type.startswith('image/')):
            await bot.reply_to(message, "⚠️ Please reply to a valid image.")
            return

        is_compressed = bool(has_photo)
        status_msg = await bot.reply_to(message, "⏳ <b>Uploading to Remaker AI...</b>", parse_mode="HTML")

        try:
            file_id = has_photo[-1].file_id if has_photo else has_document.file_id
            file_info = await bot.get_file(file_id)
            file_content = await bot.download_file(file_info.file_path)

            input_size_mb = len(file_content) / (1024 * 1024)
            await bot.edit_message_text(
                f"⏳ <b>Enhancing... You Cutie Pie</b>\n"
                f"📥 <b>Input:</b> {input_size_mb:.2f} MB\n"
                f"{'⚠️ Compressed' if is_compressed else '✅ Original quality'}",
                message.chat.id, status_msg.message_id, parse_mode="HTML"
            )

            files = {
                'type': (None, 'Enhancer'),
                'original_image_file': ('image.png', file_content, 'image/png'),
            }

            max_retries = 3
            retry_count = 0
            res_data = None

            while retry_count < max_retries:
                try:
                    headers = get_headers()
                    
                    response = await asyncio.to_thread(requests.post, 
                        'https://api.remaker.ai/api/pai/v4/ai-enhance/create-job-new',
                        headers=headers,
                        files=files,
                        timeout=20
                    )

                    res_data = response.json()

                    if res_data.get('code') == 100000:
                        break
                    
                    retry_count += 1
                    if retry_count < max_retries:
                        await bot.edit_message_text(
                            f"⏳ <b>Trying different account...</b> ({retry_count}/{max_retries})",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="HTML"
                        )
                        time.sleep(2)
                    
                except Exception as e:
                    print(f"[ENH] API request error (attempt {retry_count + 1}): {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(2)

            if res_data and res_data.get('code') == 100000:
                job_id = res_data['result']['job_id']
                success = await check_status_and_send(job_id, message.chat.id, message.message_id, user_id, username, is_compressed)

                if success:
                    try:
                        await bot.delete_message(message.chat.id, status_msg.message_id)
                    except: pass
                else:
                    await bot.edit_message_text("❌ <b>Enhancement failed or timed out.</b>", message.chat.id, status_msg.message_id, parse_mode="HTML")
            else:
                msg = res_data.get('message', 'All servers exhausted - try again later.') if res_data else "All servers exhausted."
                await bot.edit_message_text(f"❌ <b>API Error:</b> {msg}", message.chat.id, status_msg.message_id, parse_mode="HTML")

        except Exception as e:
            print(f"[ENH] Handler error: {e}")
            await bot.edit_message_text(f"❌ <b>System Error:</b> {str(e)}", message.chat.id, status_msg.message_id, parse_mode="HTML")
