import os
import requests
import time
import io
import html
import random
import asyncio

# Fix path to be absolute relative to this file to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache", "bgremove")
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

def get_random_headers(is_status_check=False):
    ua_data = random.choice(USER_AGENTS)
    headers = {
        'accept': 'application/json, text/plain, */*' if not is_status_check else '*/*',
        'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
        'dnt': '1',
        'origin': 'https://lovefaceswap.com',
        'priority': 'u=1, i',
        'referer': 'https://lovefaceswap.com/',
        'sec-ch-ua-mobile': '?1' if 'Mobile' in ua_data['user-agent'] else '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': ua_data['user-agent'],
    }
    
    if ua_data['sec-ch-ua']:
        headers['sec-ch-ua'] = ua_data['sec-ch-ua']
    
    if ua_data['sec-ch-ua-platform']:
        headers['sec-ch-ua-platform'] = ua_data['sec-ch-ua-platform']
        
    return headers

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None): 

    async def check_status_and_send(job_id, chat_id, message_id, bot, username, is_compressed=False):
        max_attempts = 40  
        attempts = 0

        while attempts < max_attempts:
            params = {'job_id': job_id}
            try:
                status_headers = get_random_headers(is_status_check=True)
                response = await asyncio.to_thread(requests.get, 'https://api.lovefaceswap.com/api/common/get', params=params, headers=status_headers)
                data = response.json()

                if data.get('code') == 200:
                    image_urls = data['data'].get('image_url', [])
                    if image_urls:
                        original_link = image_urls[0]
                        img_res = await asyncio.to_thread(requests.get, original_link)
                        img_data = img_res.content

                        file_size_mb = len(img_data) / (1024 * 1024)

                        file_stream = io.BytesIO(img_data)
                        file_stream.name = f"HD_NoBG_{job_id}.png"

                        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                        if is_compressed:
                            caption_text = (
                                "✨ <b>𝗕𝗮𝗰𝗸𝗴𝗿𝗼𝘂𝗻𝗱 𝗥𝗲𝗺𝗼𝘃𝗲𝗱</b>\n\n"
                                "⚠️ <b>𝗡𝗼𝘁𝗲:</b> You sent the image as a Photo, so Telegram compressed it.\n"
                                "📌 For full HD quality, send image as <b>𝗙𝗶𝗹𝗲/𝗗𝗼𝗰𝘂𝗺𝗲𝗻𝘁</b> next time.\n\n"
                                f"📦 <b>𝗢𝘂𝘁𝗽𝘂𝘁 𝗦𝗶𝘇𝗲:</b> {file_size_mb:.2f} MB\n"
                                f"🔗 <a href='{original_link}'>𝗢𝗿𝗶𝗴𝗶𝗻𝗮𝗹 𝗤𝘂𝗮𝗹𝗶𝘁𝘆 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱</a>\n"
                                f"\n{footer}"
                            )
                        else:
                            caption_text = (
                                "✨ <b>𝗛𝗗 𝗕𝗮𝗰𝗸𝗴𝗿𝗼𝘂𝗻𝗱 𝗥𝗲𝗺𝗼𝘃𝗲𝗱</b>\n\n"
                                "✅ Original quality preserved!\n\n"
                                f"📦 <b>𝗢𝘂𝘁𝗽𝘂𝘁 𝗦𝗶𝘇𝗲:</b> {file_size_mb:.2f} MB\n"
                                f"🔗 <a href='{original_link}'>𝗢𝗿𝗶𝗴𝗶𝗻𝗮𝗹 𝗤𝘂𝗮𝗹𝗶𝘁𝘆 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱</a>\n"
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
                elif data.get('code') in [201, 202]:
                    time.sleep(3)
                else:
                    print(f"[BGREMOVE] Unexpected code: {data.get('code')}")
                    return False
            except Exception as e:
                print(f"[BGREMOVE] Polling error: {str(e)}")
                pass

            attempts += 1
        return False

    @custom_command_handler("bgremove")
    async def bgremove_handler(message):
        if check_usage_limit and not await check_usage_limit(message, "BGRemove"):
            return

        if not message.reply_to_message:
            await bot.reply_to(message, "⚠️ Please reply to an image with the command.")
            return

        has_photo = message.reply_to_message.photo
        has_document = message.reply_to_message.document

        if not has_photo and not has_document:
            await bot.reply_to(message, "⚠️ Please reply to an image with the command.")
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        is_compressed = False

        if has_photo:
            is_compressed = True
            status_msg = await bot.reply_to(
                message, 
                "⏳ <b>Processing...</b>\n\n"
                "💡 𝗧𝗶𝗽: Send as File/Document for full HD quality",
                parse_mode="HTML"
            )
        else:
            status_msg = await bot.reply_to(message, "⏳ <b>Processing HD image...</b>", parse_mode="HTML")

        try:
            if has_photo:
                photo = message.reply_to_message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
            else:
                doc = message.reply_to_message.document
                if doc.mime_type and not doc.mime_type.startswith('image/'):
                    await bot.edit_message_text("❌ Please send an image file.", message.chat.id, status_msg.message_id)
                    return
                file_info = await bot.get_file(doc.file_id)

            file_content = await bot.download_file(file_info.file_path)

            input_size_mb = len(file_content) / (1024 * 1024)
            await bot.edit_message_text(
                f"⏳ <b>Processing...</b>\n"
                f"📥 <b>𝗜𝗻𝗽𝘂𝘁 𝘀𝗶𝘇𝗲:</b> {input_size_mb:.2f} MB\n"
                f"{'⚠️ Compressed by Telegram' if is_compressed else '✅ Original quality'}",
                message.chat.id, 
                status_msg.message_id,
                parse_mode="HTML"
            )

            # Ensure cache dir exists at runtime
            os.makedirs(CACHE_DIR, exist_ok=True)
            temp_input = os.path.join(CACHE_DIR, f"in_{message.message_id}.jpg")

            with open(temp_input, 'wb') as f:
                f.write(file_content)

            # Use randomized headers for upload
            upload_headers = get_random_headers()
            
            with open(temp_input, 'rb') as img_file:
                files = {
                    'image_input': (os.path.basename(temp_input), img_file, 'image/jpeg'),
                }

                response = await asyncio.to_thread(requests.post, 
                    'https://api.lovefaceswap.com/api/lovefaceswap/img2img/remove_bg', 
                    headers=upload_headers, 
                    files=files
                )

            res_data = response.json()

            if res_data.get('code') == 200:
                job_id = res_data['data']['job_id']
                success = await check_status_and_send(job_id, message.chat.id, message.message_id, bot, username, is_compressed)

                if success:
                    try:
                        await bot.delete_message(message.chat.id, status_msg.message_id)
                    except: pass
                else:
                    await bot.edit_message_text("❌ Failed to retrieve image after processing. Please try again.", message.chat.id, status_msg.message_id)
            else:
                msg = res_data.get('message', 'Upload failed.')
                await bot.edit_message_text(f"❌ {msg} Please try again.", message.chat.id, status_msg.message_id)

        except Exception as e:
            await bot.edit_message_text(f"❌ <b>Error:</b> {str(e)}", message.chat.id, status_msg.message_id, parse_mode="HTML")

        finally:
            if 'temp_input' in locals() and os.path.exists(temp_input):
                try:
                    os.remove(temp_input)
                except: pass