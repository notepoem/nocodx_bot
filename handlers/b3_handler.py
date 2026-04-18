import html
import requests
import time
import re
import asyncio

B3_ENDPOINTS = [
    "https://b3-checker-eight.vercel.app/check"
]

def extract_cards(text):
    """Extract cards from text using regex."""
    return re.findall(r'(\d{15,16})[|](\d{2})[|](\d{2,4})[|](\d{3,4})', text)

async def check_card_b3(card, endpoint_index, count, is_mass=False):
    """Check a single card using one of the B3 APIs"""
    try:
        parts = card.strip().split('|')
        if len(parts) != 4:
            if is_mass:
                return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ Invalid"
            return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n❌ Invalid card format.\n•━━━━━━━━━━━━━━━━━━•"

        base_api_url = B3_ENDPOINTS[endpoint_index % len(B3_ENDPOINTS)]
        params = {'card': card}

        response = await asyncio.to_thread(requests.get, base_api_url, params=params, timeout=15)
        
        if response.status_code != 200:
            if is_mass:
                return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ API Error"
            return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n❌ API Error: Status {response.status_code}\n•━━━━━━━━━━━━━━━━━━•"

        if not response.text.strip():
            if is_mass:
                return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ Empty Response"
            return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n❌ Empty response from API.\n•━━━━━━━━━━━━━━━━━━•"

        try:
            data = response.json()
        except ValueError:
            if is_mass:
                return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ Invalid Format"
            return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n❌ Invalid response format (Not JSON).\n•━━━━━━━━━━━━━━━━━━•"

        if "error" in data:
            if is_mass:
                return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ {data['error']}"
            return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n❌ {data['error']}\n•━━━━━━━━━━━━━━━━━━•"

        status = data.get("status", "Unknown")
        response_text = data.get("response", "N/A")
        gateway = data.get("gateway", "N/A")
        time_taken = data.get("time_taken", "N/A")

        bin_info = data.get("bin_info", {})
        brand = bin_info.get("brand", "N/A")
        card_type = bin_info.get("type", "N/A")
        bank = bin_info.get("bank", "N/A")
        country = bin_info.get("country", "N/A")
        emoji = bin_info.get("emoji", "")

        # Status logic
        status_emoji = ""
        if status.upper() == "APPROVED":
            status = "Live"
            status_emoji = "✅"
        else:
            status = "Dead"
            status_emoji = "❌"

        if is_mass:
            output = (
                f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n"
                f"𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n"
                f"𝗦𝘁𝗮𝘁𝘂𝘀: {status_emoji} {status}\n"
                f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {html.escape(response_text)}\n"
                f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {html.escape(country)} {emoji}"
            )
        else:
            output = (
                f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n"
                f"<code>{html.escape(card)}</code>\n\n"
                f"<b>𝗦𝘁𝗮𝘁𝘂𝘀:</b> {status_emoji} <code>{html.escape(status)}</code>\n"
                f"<b>𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲:</b> <code>{html.escape(response_text)}</code>\n"
                f"<b>𝗚𝗮𝘁𝗲𝘄𝗮𝘆:</b> <code>{html.escape(gateway)}</code>\n"
                f"<b>𝗧𝗶𝗺𝗲:</b> <code>{html.escape(time_taken)}</code>\n"
                f"•━━━━━ 𝗕𝗶𝗻 𝗜𝗻𝗳𝗼 ━━━━━•\n"
                f"<b>𝗕𝗿𝗮𝗻𝗱:</b> <code>{html.escape(brand)}</code> | <b>𝗧𝘆𝗽𝗲:</b> <code>{html.escape(card_type)}</code>\n"
                f"<b>𝗕𝗮𝗻𝗸:</b> <code>{html.escape(bank)}</code>\n"
                f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> <code>{html.escape(country)}</code> {emoji}\n"
                f"•━━━━━━━━━━━━━━━━━━•"
            )
        return output

    except Exception as e:
        if is_mass:
            return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ⚠️ Error\n𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {str(e)}"
        return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n⚠️ Error: {str(e)}\n•━━━━━━━━━━━━━━━━━━•"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("b3")
    async def handle_b3(message):
        if check_usage_limit and not await check_usage_limit(message, "B3"):
            return
        
        # Extract cards from message or reply
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await bot.reply_to(message, "❌ Provide card: <code>cc|mm|yy|cvv</code>", parse_mode="HTML")
            return

        # Take the first card found for single check
        card_tuple = found_cards[0]
        card = "|".join(card_tuple)
        
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"
        
        sent_msg = await bot.reply_to(message, "🔄 <b>Checking...</b>", parse_mode="HTML")

        status = await check_card_b3(card, 0, 1, is_mass=False)
        await bot.edit_message_text(status + "\n" + footer, sent_msg.chat.id, sent_msg.message_id, parse_mode="HTML")

    @custom_command_handler("mb3")
    async def handle_mass_b3(message):
        if check_usage_limit and not await check_usage_limit(message, "B3"):
            return

        # Extract cards from message or reply
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await bot.reply_to(message, "❌ No valid cards found.")
            return

        # Limit to 10 cards
        cards = ["|".join(c) for c in found_cards[:10]]
        
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"
        
        sent_msg = await bot.reply_to(message, f"🔄 <b>Starting Mass Check (0/{len(cards)})</b>", parse_mode="HTML")

        results = []
        for i, card in enumerate(cards):
            status = await check_card_b3(card, i, i + 1, is_mass=True)
            results.append(status)

            progress = f"🔄 <b>𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:</b> {i+1}/{len(cards)}\n\n"
            reply_text = progress + "\n\n".join(results) + "\n\n" + footer

            try:
                await bot.edit_message_text(reply_text, sent_msg.chat.id, sent_msg.message_id, parse_mode="HTML")
            except: pass

            if i < len(cards) - 1:
                time.sleep(3)
