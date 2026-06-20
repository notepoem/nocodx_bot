import html
import requests
import time
import re
import asyncio

API_URL = "https://chkr.bbinl.eu.cc/api/chkr?cc={cc}|{mm}|{yy}|{cvv}"

def extract_cards(text):
    """Extract cards from text using regex."""
    return re.findall(r'(\d{15,16})[|](\d{2})[|](\d{2,4})[|](\d{3,4})', text)

async def check_card(card, count, is_mass=False):
    """Check a single card using the updated API"""
    try:
        parts = card.strip().split('|')
        if len(parts) != 4:
            if is_mass:
                return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ Invalid"
            return "❌ Invalid card format. Use cc|mm|yy|cvv"

        cc, mm, yy, cvv = parts
        url = API_URL.format(cc=cc, mm=mm, yy=yy, cvv=cvv)
        
        # Timeout set to 25s
        response = await asyncio.to_thread(requests.get, url, timeout=35)
        data = response.json()
        
        if "message" in data and "card" not in data:
            if is_mass:
                 return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ {data['message']}"
            return f"❌ {data['message']}"

        status = data.get("status", "Unknown")
        message = data.get("message", "")
        
        status_emoji = "⚠️❓"
        if "live" in status.lower():
            status, status_emoji = "Live", "✅"
        elif "die" in status.lower() or "declined" in status.lower():
            status, status_emoji = "Dead", "❌"
        
        if status == "Unknown":
            message += "\n\n⚠️ Unknown status, please check again."
        
        if is_mass:
            return (
                f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n"
                f"𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n"
                f"<b>𝗦𝘁𝗮𝘁𝘂𝘀:</b> {status_emoji} <code>{html.escape(status)}</code>\n"
                f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {html.escape(message)}"
            )
        else:
            return (
                f"<b>𝗦𝘁𝗮𝘁𝘂𝘀:</b> <code>{html.escape(status)}</code>\n"
                f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {html.escape(message)}"
            )

    except requests.exceptions.Timeout:
        err_msg = "Connection Timeout (API is busy or slow)"
    except Exception:
        err_msg = "Service Unavailable (Please try again later)"

    # Sanitized error return to hide the API URL
    if is_mass:
        return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ⚠️ Error\n𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {err_msg}"
    return f"⚠️ {err_msg}"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("chk")
    async def handle_chk(message):
        if check_usage_limit and not await check_usage_limit(message, "Chk"):
            return
        
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await bot.reply_to(message, "❌ Provide card: <code>cc|mm|yy|cvv</code>", parse_mode="HTML")
            return

        card = "|".join(found_cards[0])
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name or str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
        
        sent_msg = await bot.reply_to(message, f"🔄 Checking <code>{card}</code>...", parse_mode="HTML")
        status = await check_card(card, 1, is_mass=False)
        
        try:
            await bot.edit_message_text(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                text=f"<b>𝗖𝗮𝗿𝗱:</b> <code>{card}</code>\n{status}\n{footer}",
                parse_mode="HTML"
            )
        except: pass

    @custom_command_handler("mas", "mchk")
    async def handle_mass_chk(message):
        if check_usage_limit and not await check_usage_limit(message, "Chk"):
            return

        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await bot.reply_to(message, "❌ No valid cards found.")
            return

        cards = ["|".join(c) for c in found_cards[:10]]
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name or str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}>"
        
        sent_msg = await bot.reply_to(message, f"🔄 <b>Starting Mass Check (0/{len(cards)})</b>", parse_mode="HTML")

        results = []
        for i, card in enumerate(cards):
            status = await check_card(card, i + 1, is_mass=True)
            results.append(status)
            progress = f"🔄 <b>𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:</b> {i+1}/{len(cards)}\n\n"
            reply_text = progress + "\n\n".join(results) + "\n\n" + footer
            try:
                await bot.edit_message_text(reply_text, sent_msg.chat.id, sent_msg.message_id, parse_mode="HTML")
            except: pass
            if i < len(cards) - 1:
                time.sleep(2)
