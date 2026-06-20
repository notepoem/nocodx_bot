import os
import html
import requests
import time
import io
import asyncio

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
    'origin': 'https://lovefaceswap.com',
    'referer': 'https://lovefaceswap.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

# state: {"step": "target"|"source", "target_bytes": bytes}
user_data = {}


def _download_bytes(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.content


def _post_swap(source_bytes, target_bytes):
    files = {
        'source_image': ('face.png',   source_bytes, 'image/png'),
        'target_image': ('target.png', target_bytes, 'image/png'),
    }
    r = requests.post(
        'https://api.lovefaceswap.com/api/face-swap/create-poll',
        headers=HEADERS, files=files, timeout=60
    )
    r.raise_for_status()
    return r.json()


def _poll_result(task_id, max_attempts=30):
    for _ in range(max_attempts):
        r = requests.get(
            'https://api.lovefaceswap.com/api/common/get',
            params={'job_id': task_id}, headers=HEADERS, timeout=30
        )
        data = r.json()
        if data.get('code') == 200:
            urls = data['data'].get('image_url', [])
            if urls:
                return urls[0]
        time.sleep(3)
    return None


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @custom_command_handler("faceswap")
    async def start_faceswap(message):
        if check_usage_limit and not await check_usage_limit(message, "FaceSwap"):
            return

        user_data[message.chat.id] = {"step": "target"}
        await bot.reply_to(
            message,
            "🖼️ <b>Step 1/2 — Target Image</b>\n\nSend the image where you want to <b>place</b> the new face.",
            parse_mode="HTML"
        )

    @bot.message_handler(
        func=lambda m: m.chat.id in user_data and user_data[m.chat.id].get("step") in ("target", "source"),
        content_types=["photo", "document"]
    )
    async def faceswap_photo_step(message):
        chat_id = message.chat.id
        state = user_data.get(chat_id, {})
        step = state.get("step")

        if not step:
            return

        # Validate image
        is_photo = bool(message.photo)
        is_doc_img = (
            message.document
            and message.document.mime_type
            and message.document.mime_type.startswith("image/")
        )
        if not (is_photo or is_doc_img):
            await bot.reply_to(message, "❌ Please send an image file.")
            return

        file_id = message.photo[-1].file_id if is_photo else message.document.file_id
        file_info = await bot.get_file(file_id)
        img_bytes = await bot.download_file(file_info.file_path)

        if step == "target":
            user_data[chat_id]["target_bytes"] = img_bytes
            user_data[chat_id]["step"] = "source"
            await bot.reply_to(
                message,
                "👤 <b>Step 2/2 — Face Image</b>\n\nNow send the image whose face you want to <b>use</b>.",
                parse_mode="HTML"
            )

        elif step == "source":
            target_bytes = state.get("target_bytes")
            user_data.pop(chat_id, None)

            if not target_bytes:
                await bot.reply_to(message, "❌ Session expired. Please start over with /faceswap.")
                return

            status_msg = await bot.reply_to(message, "⏳ Uploading and swapping faces... Please wait.")

            try:
                res_data = await asyncio.to_thread(_post_swap, img_bytes, target_bytes)

                if res_data.get('code') != 200:
                    await bot.edit_message_text(
                        "❌ API Error: Failed to create swap task.",
                        chat_id, status_msg.message_id
                    )
                    return

                task_id = res_data['data']['task_id']
                image_url = await asyncio.to_thread(_poll_result, task_id)

                if not image_url:
                    await bot.edit_message_text("❌ Task timed out. Try again.", chat_id, status_msg.message_id)
                    return

                img_data = await asyncio.to_thread(_download_bytes, image_url)
                file_stream = io.BytesIO(img_data)
                file_stream.name = f"FaceSwap_{task_id}.png"

                user = message.from_user
                username = f"@{user.username}" if user.username else (user.first_name or str(user.id))
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {html.escape(username)}"

                await bot.delete_message(chat_id, status_msg.message_id)
                await bot.send_document(
                    chat_id,
                    file_stream,
                    caption=f"✅ <b>Face Swap Complete!</b>\n\n{footer}",
                    parse_mode="HTML",
                    reply_to_message_id=message.message_id
                )

            except Exception as e:
                user_data.pop(chat_id, None)
                try:
                    await bot.edit_message_text(
                        f"❌ <b>Error:</b> {html.escape(str(e))}",
                        chat_id, status_msg.message_id, parse_mode="HTML"
                    )
                except Exception:
                    pass
