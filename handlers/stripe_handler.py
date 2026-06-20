import html
import requests
import time
import re
import random
import asyncio

STRIPE_API_ENDPOINT = "https://stripe.bbinl.eu.cc/api/stripe1"

async def safe_bot_reply(bot, message, text, parse_mode="HTML", max_retries=3):
    """Safely send message with retry logic to handle Telegram API timeouts"""
    for attempt in range(max_retries):
        try:
            return await bot.reply_to(message, text, parse_mode=parse_mode)
        except requests.exceptions.ReadTimeout:
            if attempt < max_retries - 1:
                continue
            try:
                return await bot.reply_to(message, "⚠️ Request completed but couldn't send full results due to timeout.", parse_mode=parse_mode)
            except:
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            return None
    return None

async def safe_send_message(bot, chat_id, text, parse_mode="HTML", max_retries=3):
    """Safely send new message with retry logic"""
    for attempt in range(max_retries):
        try:
            return await bot.send_message(chat_id, text, parse_mode=parse_mode)
        except requests.exceptions.ReadTimeout:
            if attempt < max_retries - 1:
                continue
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            return None
    return None

async def safe_edit_message(bot, chat_id, message_id, text, parse_mode="HTML", max_retries=2):
    """Safely edit message with retry logic"""
    for attempt in range(max_retries):
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except requests.exceptions.ReadTimeout:
            if attempt < max_retries - 1:
                continue
            return False
        except Exception as e:
            if attempt < max_retries - 1:
                continue
            return False
    return False

def extract_cards(text):
    """Extract cards from text using regex."""
    return re.findall(r'(\d{13,19})[|](\d{1,2})[|](\d{2,4})[|](\d{3,4})', text)

async def check_card_stripe(card, count=1, is_mass=False, delay_seconds=None):
    """Check card using single API endpoint with optional delay between requests"""
    
    if delay_seconds:
        time.sleep(delay_seconds)
    
    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            parts = card.strip().split('|')
            if len(parts) != 4:
                if is_mass:
                    return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ Invalid"
                return "❌ Invalid card format. Use cc|mm|yy|cvv"

            cc, mm, yy, cvv = parts

            auth_param = f"{cc}|{mm}|{yy}|{cvv}"
            url = f"{STRIPE_API_ENDPOINT}?auth={auth_param}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Connection': 'keep-alive'
            }

            response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=30)

            try:
                data = response.json()
            except ValueError:
                if response.status_code == 200:
                    if attempt < max_retries:
                        continue
                    if is_mass:
                        return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ API JSON Error"
                    return "❌ API returned invalid JSON"
                else:
                    if attempt < max_retries:
                        continue
                    if is_mass:
                        return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ HTTP {response.status_code}"
                    return f"❌ API failed with status {response.status_code}"

            if not isinstance(data, dict):
                if attempt < max_retries:
                    continue
                if is_mass:
                    return f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•\n𝗖𝗮𝗿𝗱: <code>{html.escape(card)}</code>\n𝗦𝘁𝗮𝘁𝘂𝘀: ❌ Invalid Data"
                return "❌ API returned invalid response"

            bin_info = data.get("bin_info", {})
            if not isinstance(bin_info, dict):
                bin_info = {}

            status = data.get("status", "Unknown")
            card_full = data.get("card", card)
            api_message = data.get("message", "N/A")
            payment_method_id = data.get("payment_method_id", "")
            setup_intent_id = data.get("setup_intent_id", "")

            brand = bin_info.get("brand", "N/A")
            card_type = bin_info.get("type", "N/A")
            country = bin_info.get("country", "N/A")
            bank = bin_info.get("bank", "N/A")

            if status.lower() == "success":
                status_display = "Live"
                status_emoji = "✅"
            elif status.lower() == "declined":
                status_display = "Declined"
                status_emoji = "❌"
            elif status.lower() == "error":
                status_display = "Error"
                status_emoji = "⚠️"
            else:
                status_display = f"{status}"
                status_emoji = "❓"

            if is_mass:
                output_parts = [
                    f"•━━━━━ 𝗖𝗮𝗿𝗱 {count} ━━━━━•",
                    f"𝗖𝗮𝗿𝗱: <code>{html.escape(card_full)}</code>",
                    f"𝗦𝘁𝗮𝘁𝘂𝘀: {status_emoji} {html.escape(status_display)} {status_emoji}",
                    f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {html.escape(api_message)}"
                ]
                if payment_method_id:
                    output_parts.append(f"𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗠𝗲𝘁𝗵𝗼𝗱 𝗜𝗗: <code>{html.escape(payment_method_id)}</code>")
                return "\n".join(output_parts)
            else:
                output_parts = [
                    f"💳 𝗖𝗮𝗿𝗱: <code>{html.escape(card_full)}</code>",
                    f"<b>𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲:</b> {html.escape(api_message)}",
                    f"<b>𝗦𝘁𝗮𝘁𝘂𝘀:</b> {status_emoji} {html.escape(status_display)}",
                    f"<b>𝗚𝗮𝘁𝗲𝘄𝗮𝘆:</b> Stripe Auth 0$"
                ]

                if payment_method_id:
                    output_parts.append(f"<b>𝗣𝗮𝘆𝗺𝗲𝗻𝘁 𝗠𝗲𝘁𝗵𝗼𝗱 𝗜𝗗:</b> <code>{html.escape(payment_method_id)}</code>")

                if setup_intent_id:
                    output_parts.append(f"<b>𝗦𝗲𝘁𝘂𝗽 𝗜𝗻𝘁𝗲𝗻𝘁 𝗜𝗗:</b> <code>{html.escape(setup_intent_id)}</code>")

                output_parts.extend([
                    f"•━━━━━ 𝗕𝗶𝗻 𝗜𝗻𝗳𝗼 ━━━━━•",
                    f"<b>𝗕𝗿𝗮𝗻𝗱:</b> <code>{html.escape(brand)}</code>",
                    f"<b>𝗧𝘆𝗽𝗲:</b> <code>{html.escape(card_type)}</code>",
                    f"<b>𝗕𝗮𝗻𝗸:</b> <code>{html.escape(bank)}</code>",
                    f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> <code>{html.escape(country)}</code>",
                    f"•━━━━━━━━━━━━━━━━━━•"
                ])
                return "\n".join(output_parts)

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                continue
            return "❌ Request timeout. Try again."
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                continue
            return "❌ Connection error. Try again."
        except requests.exceptions.RequestException:
            if attempt < max_retries:
                continue
            return "❌ Request failed. Try again."
        except Exception:
            if attempt < max_retries:
                continue
            return "❌ Unexpected error. Try again."

    return f"❌ API failed after {max_retries} retries"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("stripe", "st")
    async def handle_stripe(message):
        if check_usage_limit and not await check_usage_limit(message, "Stripe"):
            return
        
        # Extract cards from message or reply
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await safe_bot_reply(bot, message, "❌ Provide a card. Format: `cc|mm|yy|cvv`. Example: `/stripe 5599940472668626|08|2027|126`", parse_mode="Markdown")
            return

        # Take the first card found for single check
        card_tuple = found_cards[0]
        card = "|".join(card_tuple)
        
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲 𝗯𝘆: {username}"

        sent_msg = await safe_bot_reply(bot, message, f"🔄 Checking card with Stripe Auth 0$...", parse_mode="HTML")
        if not sent_msg:
            return

        status = await check_card_stripe(card, count=1, is_mass=False)

        await safe_edit_message(
            bot, 
            sent_msg.chat.id, 
            sent_msg.message_id, 
            f"{status}\n{footer}",
            parse_mode="HTML"
        )

    @custom_command_handler("mstripe", "mst")
    async def handle_mass_stripe(message):
        if check_usage_limit and not await check_usage_limit(message, "Stripe"):
            return

        # Extract cards from message or reply
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await safe_bot_reply(bot, message, "❌ No valid cards found.")
            return

        # Limit to 15 cards
        cards = ["|".join(c) for c in found_cards[:15]]
        
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲 𝗯𝘆: {username}"

        sent_msg = await safe_bot_reply(bot, message, f"🔄 <b>Starting Mass Check (0/{len(cards)})</b>", parse_mode="HTML")
        if not sent_msg:
            return

        results = []
        for i, card in enumerate(cards):
            delay_seconds = random.uniform(2, 4)
            status = await check_card_stripe(card, count=i + 1, is_mass=True, delay_seconds=delay_seconds)
            results.append(status)

            progress = f"🔄 <b>𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:</b> {i+1}/{len(cards)}...\n\n"
            reply_text = progress + "\n\n".join(results) + "\n\n" + footer
            
            if len(reply_text) > 4090:
                pass

            await safe_edit_message(
                bot,
                sent_msg.chat.id,
                sent_msg.message_id,
                reply_text.strip(),
                parse_mode="HTML"
            )

        # Final update
        reply_text = "\n\n".join(results) + "\n\n" + footer
        if len(reply_text) > 4090:
            pass
        
        await safe_edit_message(
            bot,
            sent_msg.chat.id,
            sent_msg.message_id,
            reply_text.strip(),
            parse_mode="HTML"
        )

