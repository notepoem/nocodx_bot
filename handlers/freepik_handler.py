import html
import asyncio
import requests
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

BASE_API   = "https://freepik.bbinl.site/api"
API_TOKEN  = "BdfwjVPHHxbtFck6X5jmVoUoGw8ttmysk2FDQFwaki3U1zvpKBuIepEXqPbeSSGB"


def _detect_type(url: str) -> str | None:
    """Return endpoint name based on Freepik URL type."""
    if "premium-photo" in url or "/photo/" in url:
        return "photo"
    if "premium-vector" in url or "/vector/" in url:
        return "vector"
    if "premium-psd" in url or "/psd/" in url:
        return "psd"
    return None


def _call_api(endpoint: str, freepik_url: str) -> dict:
    resp = requests.get(
        f"{BASE_API}/{endpoint}",
        params={"url": freepik_url, "api_token": API_TOKEN},
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("freepik", "fp", "pik")
    async def handle_freepik(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "Freepik"):
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else (user.first_name or str(user.id))
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {html.escape(username)}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().startswith("http"):
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🌐 Freepik Website", url="https://freepik.bbinl.site/"))
            await bot.reply_to(
                message,
                f"📥 <b>Freepik Downloader</b>\n\n"
                f"Send a Freepik URL to download the resource.\n\n"
                f"<b>Supported types:</b>\n"
                f"• Premium Photo\n"
                f"• Premium Vector\n"
                f"• Premium PSD\n\n"
                f"<b>Usage:</b> <code>{command_prefixes_list[0]}freepik [freepik URL]</code>\n\n"
                f"{footer}",
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True
            )
            return

        freepik_url = parts[1].strip()
        endpoint = _detect_type(freepik_url)

        if not endpoint:
            await bot.reply_to(
                message,
                "❌ <b>Unsupported URL.</b>\n\nOnly <b>premium-photo</b>, <b>premium-vector</b>, and <b>premium-psd</b> Freepik URLs are supported.",
                parse_mode="HTML"
            )
            return

        type_label = {"photo": "📷 Photo", "vector": "🖼 Vector", "psd": "🗂 PSD"}[endpoint]
        wait_msg = await bot.reply_to(message, f"⏳ Fetching {type_label}...")

        try:
            data = await asyncio.to_thread(_call_api, endpoint, freepik_url)
        except Exception as e:
            await bot.edit_message_text(
                f"❌ API error: {html.escape(str(e))}",
                chat_id=wait_msg.chat.id,
                message_id=wait_msg.message_id
            )
            return

        download_url = data.get("url")
        preview_url  = data.get("signedUrl")
        filename     = data.get("filename", "file")
        credits      = data.get("credits_remaining", "N/A")

        if not download_url:
            await bot.edit_message_text(
                "❌ No download URL in API response.",
                chat_id=wait_msg.chat.id,
                message_id=wait_msg.message_id
            )
            return

        caption = (
            f"{type_label} <b>Downloaded!</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>\n"
            f"<b>File:</b> <code>{html.escape(filename)}</code>\n"
            f"<b>Credits Left:</b> {credits}\n"
            f"<b>━━━━━━━━━━━━━━━━━</b>\n\n"
            f"{footer}"
        )

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬇️ Download", url=download_url))

        try:
            await bot.delete_message(wait_msg.chat.id, wait_msg.message_id)
        except Exception:
            pass

        if preview_url:
            try:
                await bot.send_photo(
                    message.chat.id,
                    preview_url,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup,
                    reply_to_message_id=message.message_id
                )
                return
            except Exception:
                pass

        # Fallback: text message only
        await bot.send_message(
            message.chat.id,
            caption,
            parse_mode="HTML",
            reply_markup=markup,
            reply_to_message_id=message.message_id,
            disable_web_page_preview=True
        )
