import requests
import re
import html
from telebot import types
import asyncio

API_TG = "https://telegram-story-production.up.railway.app/api/stories"
API_FB = "https://no-api.bbinl.site/api/facebook/stories"
API_IG = "https://no-api.bbinl.site/api/instagram/stories"


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("story", "fbstory", "igstory")
    async def handle_story(message):
        if check_usage_limit and not await check_usage_limit(message, "Story"):
            return

        parts_split = message.text.strip().split()
        args_raw = " ".join(parts_split[1:]).strip() if len(parts_split) > 1 else ""

        if not args_raw:
            await bot.reply_to(
                message,
                f"❓ <b>Usage:</b>\n"
                f"• Telegram: <code>{command_prefixes_list[0]}story [username]</code>\n"
                f"• Facebook: <code>{command_prefixes_list[0]}fbstory [link]</code>\n"
                f"• Instagram: <code>{command_prefixes_list[0]}igstory [link]</code>\n\n"
                f"For FB/IG you can also use <code>/story [link]</code>.",
                parse_mode="HTML"
            )
            return

        first_arg = args_raw.split()[0]
        is_url = re.match(r'https?://', first_arg)

        if is_url:
            if "facebook.com" in first_arg or "fb.watch" in first_arg:
                await process_social(bot, message, first_arg, "facebook")
            elif "instagram.com" in first_arg:
                await process_social(bot, message, first_arg, "instagram")
            else:
                await bot.reply_to(message, "❌ Unsupported URL. Only Facebook, Instagram, and Telegram usernames are supported.")
        else:
            username = first_arg.replace("@", "")
            await process_telegram(bot, message, username)


async def process_telegram(bot, message, username):
    processing_message = await bot.reply_to(
        message, f"📱 Fetching Telegram stories for @{html.escape(username)}..."
    )

    try:
        api_url = f"{API_TG}?target={username}"
        response = await asyncio.to_thread(requests.get, api_url, timeout=60)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            await bot.edit_message_text(
                chat_id=processing_message.chat.id,
                message_id=processing_message.message_id,
                text=f"❌ Failed to fetch stories: {data.get('message', 'Unknown error')}"
            )
            return

        stories = data.get("stories", [])
        total_stories = data.get("count", len(stories))

        if not stories:
            await bot.edit_message_text(
                chat_id=processing_message.chat.id,
                message_id=processing_message.message_id,
                text=f"📭 No stories found for @{html.escape(username)}"
            )
            return

        user = message.from_user
        username_footer = f"@{user.username}" if user.username else (user.first_name or str(user.id))
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {html.escape(username_footer)}"

        text = (
            f"📱 <b>Telegram Stories</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>\n"
            f"<b>User:</b> @{html.escape(username)}\n"
            f"<b>Total:</b> {total_stories}\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>\n\n"
        )

        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = []

        for idx, story in enumerate(stories[:10], 1):
            media_type = story.get("media_type", "unknown")
            date = html.escape(str(story.get("date") or "N/A"))
            story_type = str(story.get("type", ""))
            download_url = story.get("download_url")

            type_icon = "📌" if "Pinned" in story_type else "📹" if media_type == "video" else "📷"
            text += f"{idx}. {type_icon} {date}\n"

            if download_url:
                buttons.append(
                    types.InlineKeyboardButton(
                        text=f"⬇️ #{idx}",
                        url=str(download_url)
                    )
                )

        if total_stories > 10:
            text += f"\n<i>...and {total_stories - 10} more stories...</i>\n"

        text += "\n" + footer

        if buttons:
            markup.add(*buttons)

        await bot.edit_message_text(
            chat_id=processing_message.chat.id,
            message_id=processing_message.message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True
        )

    except Exception as e:
        try:
            await bot.edit_message_text(
                chat_id=processing_message.chat.id,
                message_id=processing_message.message_id,
                text=f"❌ Error: {html.escape(str(e))}"
            )
        except Exception:
            pass


async def process_social(bot, message, url, platform):
    platform_name = "Facebook" if platform == "facebook" else "Instagram"
    processing_message = await bot.reply_to(message, f"📱 Fetching {platform_name} stories/highlights...")

    api_url = API_FB if platform == "facebook" else API_IG

    try:
        req_url = f"{api_url}?url={url}"
        response = await asyncio.to_thread(requests.get, req_url, timeout=60)
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            await bot.edit_message_text(
                chat_id=processing_message.chat.id,
                message_id=processing_message.message_id,
                text="❌ Failed to fetch content."
            )
            return

        items = data.get("data", [])
        if not items:
            await bot.edit_message_text(
                chat_id=processing_message.chat.id,
                message_id=processing_message.message_id,
                text="📭 No content found."
            )
            return

        user = message.from_user
        username_footer = f"@{user.username}" if user.username else (user.first_name or str(user.id))
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {html.escape(username_footer)}"

        summary_text = (
            f"📱 <b>{html.escape(platform_name)} 𝗖𝗼𝗻𝘁𝗲𝗻𝘁</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>\n"
        )

        count = 0
        for item in items:
            for img_url in item.get("images", []):
                count += 1
                if count > 10:
                    break
                if img_url:
                    safe_img = html.escape(str(img_url), quote=True)
                    summary_text += f'{count}. 📷 <a href="{safe_img}">𝗜𝗺𝗮𝗴𝗲</a>\n'

            for vid in item.get("videos", []):
                count += 1
                if count > 10:
                    break
                qual = html.escape(vid.get("quality", "Video"))
                vid_url = vid.get("url")
                if vid_url:
                    safe_vid = html.escape(str(vid_url), quote=True)
                    summary_text += f'{count}. 📹 <a href="{safe_vid}">{qual}</a>\n'

            if count > 10:
                break

        summary_text += "<b>━━━━━━━━━━━━━━━━━</b>\n"
        summary_text += "\n" + footer

        await bot.edit_message_text(
            chat_id=processing_message.chat.id,
            message_id=processing_message.message_id,
            text=summary_text,
            parse_mode="HTML",
            disable_web_page_preview=False
        )

    except Exception as e:
        await bot.edit_message_text(
            chat_id=processing_message.chat.id,
            message_id=processing_message.message_id,
            text=f"❌ Error: {html.escape(str(e))}"
        )
