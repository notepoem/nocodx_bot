import os
import asyncio
import aiohttp
import logging
import tempfile
import html
import random
import telebot
from typing import Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Valid cross-platform path relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache", "pfp")
os.makedirs(CACHE_DIR, exist_ok=True)

FB_PFP_API = "https://fb-unlock-ashen.vercel.app/api/fb?url={url}"
INSTA_PFP_API = "https://fb-unlock-ashen.vercel.app/api/ig?url={url}"

def get_random_formatted_message(user_details: Dict[str, Any]) -> str:
    def get_safe_value(key: str, default: str = 'N/A') -> str:
        value = user_details.get(key, default)
        if isinstance(value, str):
            if key == 'from' and value.startswith('From'):
                value = value.replace('From', '', 1).strip()
            if key == 'lives_in' and value.startswith('Lives in'):
                value = value.replace('Lives in', '', 1).strip()
        return html.escape(str(value))

    name = get_safe_value('name')
    bio = get_safe_value('bio')
    friends_count = get_safe_value('friends_count')
    relationship_status = get_safe_value('relationship_status')
    from_loc = get_safe_value('from')
    lives_in_loc = get_safe_value('lives_in')
    work = get_safe_value('work')
    education = get_safe_value('education')
    user_id = user_details.get('user_id', 'N/A')

    format_1 = (
        f"╔═════════ {name} ═════════╗\n"
        f"║           - - - - - - - - - - - - - - - - - - - - - -          ║\n"
        f"║  𝗕𝗶𝗼: {bio}\n"
        f"║  𝗦𝘁𝗮𝘁𝘂𝘀: {relationship_status}\n"
        f"║  𝗙𝗿𝗶𝗲𝗻𝗱𝘀: {friends_count}\n"
        f"║  𝗙𝗿𝗼𝗺: {from_loc}\n"
        f"║  𝗟𝗶𝘃𝗲𝘀 𝗶𝗻: {lives_in_loc}\n"
        f"║  𝗪𝗼𝗿𝗸: {work}\n"
        f"║  𝗘𝗱𝘂𝗰𝗮𝘁𝗶𝗼𝗻: {education}\n"
        f"║  𝗜𝗗: <code>{html.escape(str(user_id))}</code>\n"
        f"║           - - - - - - - - - - - - - - - - - - - - - -          ║\n"
        f"╚═══════════════════════════╝"
    )

    format_2 = (
        f"✦─ <b>{name}</b> ─✦\n"
        f"═════════════════════\n"
        f"• 𝗯𝗶𝗼: {bio}\n"
        f"• 𝗳𝗿𝗶𝗲𝗻𝗱𝘀: {friends_count}\n"
        f"• 𝗿𝗲𝗹𝗮𝘁𝗶𝗼𝗻𝘀𝗵𝗶𝗽: {relationship_status}\n"
        f"• 𝗳𝗿𝗼𝗺: {from_loc}\n"
        f"• 𝗹𝗶𝘃𝗲 𝗶𝗻: {lives_in_loc}\n"
        f"• 𝘄𝗼𝗿𝗸: {work}\n"
        f"• 𝘀𝘁𝘂𝗱𝗶𝗲𝗱: {education}\n"
        f"• 𝗜𝗗: <code>{html.escape(str(user_id))}</code>\n"
        f"━━━━━━━ • ❖ • ━━━━━━━"
    )

    format_3 = (
        f"╭─❪ <b>{name}'s 𝗣𝗿𝗼𝗳𝗶𝗹𝗲</b> ❫─────────╮\n"
        f"  ⫷ 𝗕𝗶𝗼: {bio} ⫸\n"
        f"  ⫷ 𝗙𝗿𝗼𝗺: {from_loc} | 𝗹𝗶𝘃𝗲 𝗶𝗻: {lives_in_loc} ⫸\n"
        f"  ⫷  𝗦𝘁𝗮𝘁𝘂𝘀: {relationship_status}  | 𝗙𝗿𝗶𝗲𝗻𝗱𝘀: {friends_count} ⫸\n"
        f"  ⫷ 𝗦𝘁𝘂𝗱𝗲𝗻𝘁 𝗮𝘁: {education} ⫸\n"
        f"  ⫷  𝗜𝗗: <code>{html.escape(str(user_id))}</code> ⫸\n"
        f"╰────────────────────────────────╯"
    )

    format_4 = (
        f"━━━━ <b>{name}</b> ━━━━\n"
        f"━━━ 𝗕𝗶𝗼: {bio} ━━━\n"
        f"* 𝗦𝘁𝗮𝘁𝘂𝘀: {relationship_status}\n"
        f"* 𝗙𝗿𝗼𝗺: {from_loc}\n"
        f"* 𝗹𝗶𝘃𝗲 𝗶𝗻: {lives_in_loc}\n"
        f"* 𝗪𝗼𝗿𝗸𝘀 𝗮𝘀 𝗮 {work}\n"
        f"* 𝗦𝘁𝘂𝗱𝗶𝗲𝗱 𝗮𝘁 {education}\n"
        f"* 𝗜𝗗: <code>{html.escape(str(user_id))}</code>\n"
        f"━━━━━━━ • ❖ • ━━━━━━━"
    )

    formats = [format_1, format_2, format_3, format_4]

    return random.choice(formats)

async def get_profile_picture(url: str) -> Dict[str, Any]:
    try:
        parsed_url = urlparse(url)
        image_paths = []

        if "instagram.com" in parsed_url.netloc:
            api_url = INSTA_PFP_API.format(url=url)
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as res:
                    if res.status == 404:
                        return {"status": "error", "error": "❌ Instagram profile not found or username is incorrect."}
                    res.raise_for_status()
                    image_bytes = await res.read()

                    temp_path = os.path.join(CACHE_DIR, f"insta_{random.randint(1000, 9999)}.jpg")
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    with open(temp_path, "wb") as f:
                        f.write(image_bytes)
                    image_paths.append(temp_path)
                    return {"status": "success", "image_paths": image_paths, "message": "✅ Success! Here is your profile picture."}

        elif "facebook.com" in parsed_url.netloc:
            api_url = FB_PFP_API.format(url=url)
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as res:
                    res.raise_for_status()
                    data = await res.json()

                    user_details = data.get("user_details", {})
                    user_id = user_details.get("user_id", "N/A")

                    if not user_details or user_id == "N/A":
                        error_message = data.get("error", "❌ API থেকে কোনো তথ্য পাওয়া যায়নি।")
                        return {"status": "error", "error": error_message}

                    user_id_message = f"ID: <code>{html.escape(str(user_id))}</code>"

                    if data.get("profile_status") == "public":
                        return {"status": "success", "image_paths": [], "message": f"⚠️ This is a public profile.\n{user_id_message}"}

                    if data.get("status") == "success":
                        image_urls = []
                        user_details_message = get_random_formatted_message(user_details)

                        if isinstance(data.get("profile_picture"), list) and len(data["profile_picture"]) > 0:
                            image_urls.append(data["profile_picture"][0])
                        if data.get("cover_photo") and data["cover_photo"].get("url"):
                            image_urls.append(data["cover_photo"]["url"])

                        if not image_urls:
                            message = f"✅ Success! No photos found, only profile details available.\n{user_details_message}"
                            return {"status": "success", "image_paths": [], "message": message}

                        downloaded_count = 0
                        for img_url in image_urls:
                            try:
                                async with aiohttp.ClientSession() as img_session:
                                    async with img_session.get(img_url) as img_res:
                                        img_res.raise_for_status()
                                        image_bytes = await img_res.read()
                                        temp_path = os.path.join(CACHE_DIR, f"fb_{random.randint(1000, 9999)}.jpg")
                                        os.makedirs(CACHE_DIR, exist_ok=True)
                                        with open(temp_path, "wb") as f:
                                            f.write(image_bytes)
                                        image_paths.append(temp_path)
                                        downloaded_count += 1
                            except aiohttp.ClientResponseError as e:
                                logger.warning(f"Failed to download image from {img_url}: {e}")
                                continue

                        if downloaded_count == 0:
                            message = f"❌ Failed to download images. Please try again.\n{user_id_message}"
                            return {"status": "success", "image_paths": [], "message": message}

                        if downloaded_count == 2:
                            message = f"✅ Success! Here are your profile and cover photos.\n{user_details_message}"
                        elif downloaded_count == 1:
                            message = f"✅ Success! However, only one photo was found.\n{user_details_message}"

                        return {"status": "success", "image_paths": image_paths, "message": message}
                    else:
                        error_message = data.get("error", "❌ API থেকে কোনো তথ্য পাওয়া যায়নি।")
                        return {"status": "error", "error": error_message}
        else:
            return {"status": "error", "error": "❌ Please provide a Facebook or Instagram profile URL."}

    except Exception as e:
        return {"status": "error", "error": f"❌ An unexpected error occurred: {str(e)}. Please try again."}


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @custom_command_handler("pfp")
    async def handle_pfp_command(message):
        if check_usage_limit and not await check_usage_limit(message, "Pfp"):
            return
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             query = " ".join(parts_split[1:]).strip()
        else:
             query = ""

        if not query:
            await bot.reply_to(
                message,
                "❌ Please provide a Facebook or Instagram profile URL. Example: `/pfp https://www.facebook.com/...`",
                parse_mode="Markdown")
            return

        thinking_message = await bot.reply_to(message, "⏳ Downloading profile picture...")

        image_paths = []
        try:
            result = await get_profile_picture(query)

            if result['status'] == 'success':
                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                image_paths = result['image_paths']
                caption_text = result['message'] + footer

                if image_paths:
                    if len(image_paths) > 1:
                        media_group = [telebot.types.InputMediaPhoto(open(path, 'rb')) for path in image_paths]
                        media_group[0].caption = caption_text
                        media_group[0].parse_mode = "HTML"
                        await bot.send_media_group(
                            message.chat.id,
                            media_group,
                            reply_to_message_id=message.message_id
                        )
                    else:
                        with open(image_paths[0], 'rb') as f:
                            await bot.send_photo(
                                message.chat.id,
                                f,
                                caption=caption_text,
                                reply_to_message_id=message.message_id,
                                parse_mode="HTML"
                            )
                else:
                    await bot.send_message(
                        message.chat.id,
                        caption_text,
                        reply_to_message_id=message.message_id,
                        parse_mode="HTML"
                    )

                await bot.delete_message(thinking_message.chat.id, thinking_message.message_id)
            else:
                await bot.edit_message_text(chat_id=thinking_message.chat.id, message_id=thinking_message.message_id, text=result['error'])
        except Exception as e:
            await bot.edit_message_text(chat_id=thinking_message.chat.id, message_id=thinking_message.message_id, text=f"❌ An unexpected error occurred: {str(e)}. Please try again.")
        finally:
            for path in image_paths:
                if os.path.exists(path):
                    os.remove(path)