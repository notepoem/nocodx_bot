import requests
import re
import asyncio

API_KEY = "f21336f30f22e88242c0868a5b7475b5"
API_BASE = "https://api.forexrateapi.com/v1/latest"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("exchange", "convert", "currency")
    async def handle_exchange(message):
        if check_usage_limit and not await check_usage_limit(message, "Exchange"):
            return
        
        # New command parsing logic
        parts_split = message.text.strip().split(maxsplit=1) # Split only once to separate command from args
        if len(parts_split) > 1:
            args_raw = parts_split[1].strip()
        else:
            args_raw = ""

        if not args_raw:
            await bot.reply_to(
                message, 
                f"❓ <b>Usage:</b>\n"
                f"<code>{command_prefixes_list[0]}exchange USD</code> - All rates for USD\n"
                f"<code>{command_prefixes_list[0]}exchange 100 USD</code> - All rates × 100\n"
                f"<code>{command_prefixes_list[0]}exchange 100 USD BDT</code> - Specific conversion", 
                parse_mode="HTML"
            )
            return

        match_with_amount = re.match(r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]{3})(?:\s+([a-zA-Z]{3}))?$', args_raw)
        match_currency_only = re.match(r'^([a-zA-Z]{3})$', args_raw)
        
        processing_message = await bot.reply_to(message, "� <b>Fetching exchange rates...</b>", parse_mode="HTML")

        try:
            if match_currency_only:
                base_currency = match_currency_only.group(1).upper()
                url = f"{API_BASE}?api_key={API_KEY}&base={base_currency}"
                response = await asyncio.to_thread(requests.get, url, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if not data.get("success"):
                    raise Exception("API returned unsuccessful response")
                
                rates = data.get("rates", {})
                base = data.get("base", base_currency)
                
                rate_lines = []
                for curr, rate in sorted(rates.items()):
                    if curr != base:
                        rate_lines.append(f"• <b>{curr}:</b> <code>{rate:,.6f}</code>")
                
                if len(rate_lines) > 50:
                    rate_lines = rate_lines[:50]
                    rate_lines.append("... and more")
                
                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                result_text = (
                    f"💱 <b>𝗘𝘅𝗰𝗵𝗮𝗻𝗴𝗲 𝗥𝗮𝘁𝗲𝘀 𝗳𝗼𝗿 {base}</b>\n\n"
                    + "\n".join(rate_lines) +
                    f"\n{footer}"
                )
                
                await bot.edit_message_text(
                    chat_id=processing_message.chat.id,
                    message_id=processing_message.message_id,
                    text=result_text,
                    parse_mode="HTML"
                )
                
            elif match_with_amount:
                amount = float(match_with_amount.group(1))
                base_currency = match_with_amount.group(2).upper()
                target_currency = match_with_amount.group(3).upper() if match_with_amount.group(3) else None
                
                if target_currency:
                    url = f"{API_BASE}?api_key={API_KEY}&base={base_currency}&currencies={target_currency}"
                    response = await asyncio.to_thread(requests.get, url, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    if not data.get("success"):
                        raise Exception("API returned unsuccessful response")
                    
                    rates = data.get("rates", {})
                    rate = rates.get(target_currency, 1)
                    converted = amount * rate
                    
                    user = message.from_user
                    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                    footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                    result_text = (
                        f"💱 <b>𝗖𝘂𝗿𝗿𝗲𝗻𝗰𝘆 𝗖𝗼𝗻𝘃𝗲𝗿𝘀𝗶𝗼𝗻</b>\n•──────────────────────•\n"
                        f"<b>𝗙𝗿𝗼𝗺:</b> <code>{amount:,.2f} {base_currency}</code>\n"
                        f"<b>𝗧𝗼:</b> <code>{converted:,.2f} {target_currency}</code>\n"
                        f"<b>𝗥𝗮𝘁𝗲:</b> 1 {base_currency} = <code>{rate:,.6f}</code> {target_currency}\n"
                        f"\n{footer}"
                    )
                else:
                    url = f"{API_BASE}?api_key={API_KEY}&base={base_currency}"
                    response = await asyncio.to_thread(requests.get, url, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    
                    if not data.get("success"):
                        raise Exception("API returned unsuccessful response")
                    
                    rates = data.get("rates", {})
                    base = data.get("base", base_currency)
                    
                    rate_lines = []
                    for curr, rate in sorted(rates.items()):
                        if curr != base:
                            converted = amount * rate
                            rate_lines.append(f"• <b>{curr}:</b> <code>{converted:,.2f}</code>")
                    
                    if len(rate_lines) > 50:
                        rate_lines = rate_lines[:50]
                        rate_lines.append("... and more")
                    
                    user = message.from_user
                    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                    footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                    result_text = (
                        f"💱 <b>{amount:,.2f} {base} 𝗖𝗼𝗻𝘃𝗲𝗿𝘁𝗲𝗱</b>\n\n"
                        + "\n".join(rate_lines) +
                        f"\n{footer}"
                    )
                
                await bot.edit_message_text(
                    chat_id=processing_message.chat.id,
                    message_id=processing_message.message_id,
                    text=result_text,
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=processing_message.chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ <b>Invalid format. Use:</b>\n"
                         f"<code>{command_prefixes_list[0]}exchange USD</code>\n"
                         f"<code>{command_prefixes_list[0]}exchange 100 USD</code>\n"
                         f"<code>{command_prefixes_list[0]}exchange 100 USD BDT</code>",
                    parse_mode="HTML"
                )
                
        except requests.exceptions.RequestException as e:
            try:
                await bot.edit_message_text(
                    chat_id=processing_message.chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ <b>API request failed:</b> {str(e)}",
                    parse_mode="HTML"
                )
            except:
                await bot.reply_to(message, f"❌ API request failed: {str(e)}")
        except Exception as e:
            try:
                await bot.edit_message_text(
                    chat_id=processing_message.chat.id,
                    message_id=processing_message.message_id,
                    text=f"❌ <b>Error:</b> {str(e)}",
                    parse_mode="HTML"
                )
            except:
                await bot.reply_to(message, f"❌ Error: {str(e)}")
