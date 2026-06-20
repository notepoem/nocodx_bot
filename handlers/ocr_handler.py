import requests
import random
import system_manager
import json
import re
import os
import uuid
import hmac
import hashlib
import base64
import io
import time
import subprocess

from datetime import datetime, timezone
import asyncio

# Robust path for cache directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache", "ocr")
os.makedirs(CACHE_DIR, exist_ok=True)

PROMPTS = {
    'ocr': '\nYou are an expert in image text recognition. Please review the uploaded image and extract and output only all the text information contained in the image. Do not add any explanations, summaries or other content. Only return the recognized plain text content.\n',
    'video_ocr': """You are an expert in Video Text Recognition and Translation.
Please analyze the uploaded video/GIF and perform the following:
1. **Extract Text**: Identify and write down all the text found in the video EXACTLY as it appears (same language/script).
2. **Translate**: Provide a complete English translation of the extracted text.
3. **Context**: Briefly describe what is happening in the video (visual summary).

**Format your response exactly like this:**
<b>Original Text:</b>
[Extracted text here]

<b>English Translation:</b>
[English translation here]

<b>Visual Context:</b>
[Brief description of the scene]
""",
    'summary': """You are an **expert in summarizing Text Content**, skilled at extracting key information and generating **high-quality, well-structured summaries**.
Based on the provided Text Content, complete the following tasks:

**Task Description:**
Generate a professional, credible summary of the following content. The output must be strictly grounded in the source—no fabrication.
**Formatting Rules (Telegram HTML):**
- **DO NOT** use Markdown (no `###`, `**`, `| table |`).
- Use **HTML tags** specifically: `<b>bold</b>`, `<i>italic</i>`, `<u>underline</u>`, `<code>code</code>`.
- **Headers**: Use `<b>Header Name</b>` (e.g., <b>Summary</b>, <b>Key Features</b>).
- **Tables**: Do NOT use tables. Convert tables to list format or "Key: Value" lines.
- **Lists**: Use standard bullet points (• or -).
- **Bold** key insights, terms, and conclusions using `<b>`.

**Structure:**
- <b>Summary</b> followed by the summary text.
- <b>Key Features/Insights</b> followed by a bulleted list.
- <b>Pricing/Data</b> (if any) formatted as a clean list.

Length: - Ensure the response has a minimum of 400 words
Depth: - The response should be brief in detail.

Language: - The entire output must be written in the "English" language.
- Do **not** include any separators (`---`), or additional text outside of the task results.

Text Content:
"""
}

class NoteGPTService:
    def __init__(self):
        self.base_url = "https://notegpt.io"
        self.api_url = "https://api.journeydraw.ai/chatgpt/v4/question"
        self.user_agent = self._get_random_user_agent()
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'dnt': '1',
            'origin': self.base_url,
            'referer': f'{self.base_url}/',
            'user-agent': self.user_agent,
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        self.cookies = {
            'anonymous_user_id': str(uuid.uuid4()),
        }

    def _get_random_user_agent(self):
        """Generates a dynamic random User-Agent string."""
        chrome_version = f"{random.randint(120, 144)}.0.{random.randint(0, 5000)}.{random.randint(0, 200)}"
        return f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36'

    async def get_config(self):
        """Fetches dynamic configuration (sign, secret_key, etc.)."""
        url = f'{self.base_url}/api/v1/ai-tab/get-prod-config'
        try:
            headers = self.headers.copy()
            headers['referer'] = f'{self.base_url}/pdf-summary'
            
            response = await asyncio.to_thread(requests.get, url, headers=headers, cookies=self.cookies, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('code') == 100000:
                return data['data']
            else:
                raise Exception(f"Config fetch failed: {data}")
        except Exception as e:
            print(f"[-] Error fetching config: {e}")
            raise

    async def get_sts_token_plain(self):
        """Fetches STS token from the unencrypted endpoint."""
        url = f"{self.base_url}/api/v1/oss/sts-token"
        try:
            res = await asyncio.to_thread(requests.get, url, headers=self.headers, cookies=self.cookies, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if data.get('code') == 100000:
                    return data['data']
            return None
        except Exception:
            return None

    def get_oss_signature(self, key_secret, verb, content_md5, content_type, date, canonical_headers, canonical_resource):
        """Calculates Aliyun OSS Signature V1."""
        string_to_sign = f"{verb}\n{content_md5}\n{content_type}\n{date}\n{canonical_headers}{canonical_resource}"
        signature = base64.b64encode(hmac.new(key_secret.encode(), string_to_sign.encode(), hashlib.sha1).digest()).decode()
        return signature

    async def upload_file_oss(self, file_path, sts_info, content_type='application/pdf'):
        """Uploads a file (PDF/GIF/Image) to Aliyun OSS with proper signing."""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()

            file_uuid = str(uuid.uuid4())
            bucket_name = "nc-cdn"
            
            # Determine folder and extension based on content_type
            if 'image' in content_type:
                 ext = 'gif' if 'gif' in content_type else 'jpg'
                 object_path = f"notegpt/web3in1/image/{file_uuid}.{ext}"
            else:
                 object_path = f"notegpt/web3in1/pdf/{file_uuid}.pdf"

            bucket_url = f"https://{bucket_name}.oss-us-west-1.aliyuncs.com"
            upload_url = f"{bucket_url}/{object_path}"

            # OSS Headers
            date_str = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
            security_token = sts_info['SecurityToken']
            
            canonical_headers = f"x-oss-security-token:{security_token}\n"
            canonical_resource = f"/{bucket_name}/{object_path}"
            
            signature = self.get_oss_signature(
                sts_info['AccessKeySecret'],
                "PUT",
                "",
                content_type,
                date_str,
                canonical_headers,
                canonical_resource
            )

            headers = {
                'Authorization': f"OSS {sts_info['AccessKeyId']}:{signature}",
                'Date': date_str,
                'x-oss-security-token': security_token,
                'Content-Type': content_type,
                'User-Agent': 'aliyun-sdk-js/6.23.0',
            }
            
            response = await asyncio.to_thread(requests.put, upload_url, data=file_content, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Return full URL for images, path for PDFs (service behavior dependent)
            if 'image' in content_type:
                 return f"{bucket_url}/{object_path}"
            else:
                 return f"/{object_path}"
                 
        except Exception as e:
            print(f"[-] Upload failed: {e}")
            return None

    async def convert_pdf(self, oss_path):
        """Converts uploaded PDF on NoteGPT."""
        url = f"{self.base_url}/api/v1/pdf-convert"
        params = {'path': oss_path, 'type': 1}
        try:
            res = await asyncio.to_thread(requests.get, url, params=params, headers=self.headers, cookies=self.cookies, timeout=20)
            if res.status_code == 200:
                return res.json()
            return None
        except Exception:
            return None

    async def _make_api_call(self, params, json_data):
        """Internal method to make the actual API call (OCR/Summary)."""
        try:
            response = await asyncio.to_thread(requests.post, self.api_url, params=params, headers=self.headers, json=json_data, stream=True, timeout=60)
            
            full_text = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_str = decoded_line[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data_json = json.loads(data_str)
                            content = data_json.get('message', '')
                            full_text += content
                        except json.JSONDecodeError:
                            pass
            return full_text

        except Exception as e:
            print(f"[-] Request Failed: {e}")
            return None

    async def process_image(self, image_url, mode='ocr'):
        """Process an image URL with the specified mode (OCR or Summary)."""
        config = await self.get_config()
        
        params = {
            't': config['t'],
            'nonce': config['nonce'],
            'sign': config['sign'],
            'secret_key': config['secret_key'],
            'app_id': config['app_id'],
            'uid': config['uid'],
        }

        prompt_text = PROMPTS.get(mode, PROMPTS['ocr'])

        json_data = {
            'text': prompt_text,
            'end_flag': True,
            'streaming': True,
            'model': 'gpt-4.1-mini',
            'image_url': image_url,
        }

        return await self._make_api_call(params, json_data)

    async def process_text_summary(self, text):
        """Summarize plain text."""
        config = await self.get_config()

        params = {
            't': config['t'],
            'nonce': config['nonce'],
            'sign': config['sign'],
            'secret_key': config['secret_key'],
            'app_id': config['app_id'],
            'uid': config['uid'],
        }

        prompt = PROMPTS['summary']
        json_data = {
            'text': prompt + text,
            'end_flag': True,
            'streaming': True,
            'model': 'gpt-4.1-mini',
        }

        return await self._make_api_call(params, json_data)


def convert_video_to_gif(video_path):
    """Converts video to optimized GIF using ffmpeg."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        output_path = f"{os.path.splitext(video_path)[0]}.gif"
        
        # Use centralized ffmpeg path
        ffmpeg_cmd = system_manager.FFMPEG_EXE

        command = [
            ffmpeg_cmd, '-y', '-i', video_path,
            '-vf', 'fps=8,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
            '-loop', '0', output_path
        ]

        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"Error converting video to GIF: {e}")
        return None

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    service = NoteGPTService()

    async def get_target_info(message):
        """Analyzes the message to find an image URL or a PDF file."""
        try:
            # 1. Reply to Document (PDF)
            if message.reply_to_message and message.reply_to_message.document:
                 doc = message.reply_to_message.document
                 if doc.mime_type == 'application/pdf':
                     return 'pdf_file_id', doc.file_id

            if message.reply_to_message:
                reply = message.reply_to_message
                
                # Video/Animation Reply
                if reply.video:
                     return 'video_file_id', reply.video.file_id
                if reply.animation:
                     return 'video_file_id', reply.animation.file_id
                if reply.document and reply.document.mime_type and reply.document.mime_type.startswith('video/'):
                     return 'video_file_id', reply.document.file_id

                if reply.photo:
                    photo = reply.photo[-1]
                    try:
                        file_info = await bot.get_file(photo.file_id)
                        return 'url', f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
                    except Exception as e:
                        print(f"Error getting file info: {e}")
                        return None, None
                
                if reply.document and reply.document.mime_type and reply.document.mime_type.startswith('image/'):
                    try:
                        file_info = await bot.get_file(reply.document.file_id)
                        return 'url', f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
                    except Exception as e:
                        print(f"Error getting file info: {e}")
                        return None, None

                if reply.text:
                    urls = re.findall(r'(https?://\S+)', reply.text)
                    if urls:
                        return 'url', urls[0]

            # Direct Video? Usually commands are caption attached, but let's check basic text logic
            parts = message.text.split(maxsplit=1)
            if len(parts) > 1:
                possible_url = parts[1].strip()
                if possible_url.startswith("http"):
                    return 'url', possible_url
            
            return None, None
        except Exception as e:
            print(f"Error in get_target_info: {e}")
            return None, None

    async def send_result_safe(chat_id, text, mode, reply_to_message_id=None):
        """Sends the result, determining whether to send as message or file."""
        header = "📝 <b>OCR Result:</b>\n•──────────────────────•" if mode == 'ocr' else "📑 <b>Summary Result:</b>\n•──────────────────────•"
        
        # Telegram text limit ~4096. 
        if len(text) > 4000:
            try:
                bio = io.BytesIO(text.encode('utf-8'))
                bio.name = 'result.txt' # Important for Telegram to recognize it
                caption = f"{header}\n(Result too long, sent as file)"
                await bot.send_document(chat_id, bio, caption=caption, parse_mode='HTML', reply_to_message_id=reply_to_message_id)
            except Exception as e:
                await bot.send_message(chat_id, f"❌ Error sending file: {e}", reply_to_message_id=reply_to_message_id)
        else:
            # Send as text
            full_msg = f"{header}\n\n{text}"
            await bot.send_message(chat_id, full_msg, parse_mode='HTML', reply_to_message_id=reply_to_message_id)

    async def process_ocr_command(message, mode):
        if check_usage_limit and not await check_usage_limit(message, "OCR"):
            return

        chat_id = message.chat.id
        target_type, target_content = await get_target_info(message)

        if not target_type:
            await bot.reply_to(message, "❌ <b>Please provide an image, video, or PDF!</b>\n\nYou can:\n1. Reply to media\n2. Send URL", parse_mode="HTML")
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        # footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>" 

        status_msg = await bot.reply_to(message, "🔄 <b>Processing...</b>", parse_mode="HTML")

        try:
            result_text = None

            if target_type == 'url':
                 result_text = await service.process_image(target_content, mode=mode)
            
            elif target_type == 'video_file_id':
                await bot.edit_message_text("⬇️ <b>Downloading Video...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                file_info = await bot.get_file(target_content)
                downloaded_file = await bot.download_file(file_info.file_path)
                
                ext = os.path.splitext(file_info.file_path)[1]
                if not ext: ext = ".mp4"
                
                os.makedirs(CACHE_DIR, exist_ok=True)
                temp_filename = os.path.join(CACHE_DIR, f"temp_vid_{uuid.uuid4()}{ext}")
                try:
                    with open(temp_filename, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    
                    await bot.edit_message_text("⚙️ <b>Converting to GIF...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                    gif_path = convert_video_to_gif(temp_filename)
                    
                    if not gif_path:
                         raise Exception("Video conversion failed.")

                    sts = await service.get_sts_token_plain()
                    if sts:
                        await bot.edit_message_text("☁️ <b>Uploading to Cloud...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                        # Upload as image/gif
                        oss_url = await service.upload_file_oss(gif_path, sts, content_type='image/gif')
                        
                        if oss_url:
                             await bot.edit_message_text("👀 <b>Analyzing Video...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                             # Use special video prompt
                             result_text = await service.process_image(oss_url, mode='video_ocr')
                        else:
                             raise Exception("Cloud Upload failed.")
                    else:
                        raise Exception("STS Token failed.")

                    if os.path.exists(gif_path):
                         os.remove(gif_path)

                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

            elif target_type == 'pdf_file_id':
                file_info = await bot.get_file(target_content)
                if file_info.file_size and file_info.file_size > 20 * 1024 * 1024:
                    await bot.edit_message_text("❌ <b>File too large!</b> Limit is 20MB.", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                    return
                # ... (rest of PDF logic mostly same, just calling new upload method)
                await bot.edit_message_text("⬇️ <b>Downloading PDF...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                downloaded_file = await bot.download_file(file_info.file_path)
                os.makedirs(CACHE_DIR, exist_ok=True)
                temp_filename = os.path.join(CACHE_DIR, f"temp_{uuid.uuid4()}.pdf")
                try:
                    with open(temp_filename, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    
                    sts = await service.get_sts_token_plain()
                    if sts:
                        await bot.edit_message_text("☁️ <b>Uploading to Cloud...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                        oss_path = await service.upload_file_oss(temp_filename, sts, content_type='application/pdf')
                        if oss_path:
                            await bot.edit_message_text("⚙️ <b>Converting PDF...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                            res_convert = await service.convert_pdf(oss_path)
                            if res_convert:
                                data = res_convert.get('data', {})
                                text_content = data.get('content', '')
                                if not text_content:
                                    pages = data.get('pages', [])
                                    text_content = " ".join([p.get('text', '') for p in pages])
                                
                                if not text_content:
                                     raise Exception("No text found in PDF.")

                                if mode == 'ocr':
                                    result_text = text_content
                                else:
                                    await bot.edit_message_text("🧠 <b>Summarizing...</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                                    result_text = await service.process_text_summary(text_content)
                            else:
                                raise Exception("PDF Conversion failed.")
                        else:
                            raise Exception("Bypass Upload failed.")
                    else:
                        raise Exception("Failed to get STS.")
                
                finally:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

            # Send Result
            if result_text:
                full_text = f"{result_text}\n\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                await bot.delete_message(chat_id, status_msg.message_id)
                await send_result_safe(chat_id, full_text, mode, reply_to_message_id=message.message_id)
            else:
                 await bot.edit_message_text("❌ <b>Failed to process request.</b>", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")

        except Exception as e:
            await bot.edit_message_text(f"❌ <b>Error:</b> {str(e)}", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")


    @custom_command_handler("ocr", "txt")
    async def handle_ocr_cmd(message):
        await process_ocr_command(message, mode='ocr')

    @custom_command_handler("summ")
    async def handle_summ_cmd(message):
        await process_ocr_command(message, mode='summary')
