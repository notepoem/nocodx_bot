import requests
import html
import re
from telebot.types import Message
import asyncio

async def fetch_vbv_status(card_input):
    """Helper function to fetch and categorize VBV status."""
    try:
        api_url = f"https://vbv.bbinl.eu.cc/api/vbv4?cc={card_input}"
        response = await asyncio.to_thread(requests.get, api_url, timeout=20)
        
        if response.status_code != 200:
            try:
                err_data = response.json()
                err_msg = err_data.get("message") or err_data.get("error") or f"HTTP {response.status_code}"
            except:
                err_msg = f"HTTP {response.status_code}"
            return {"success": False, "error": f"API Error: {err_msg}"}

        res_data = response.json()
        if res_data.get("status") != "success":
            return {"success": False, "error": res_data.get("message") or "API reported failure."}

        details = res_data.get("details") or {}
        status = (details.get("3ds_status") or "").lower()
        raw_result = res_data.get("result") or "N/A"
        result_val = f"{raw_result} ({status})" if status else raw_result

        # Categorization
        approved_list = ["authenticate_successful", "authenticate_passed", "authenticate_approved", "authenticate_verified", "frictionless_successful"]
        not_approved_list = ["authenticate_rejected", "authenticate_frictionless_failed", "authenticate_attempt_failed", "lookup_error"]
        attempted_list = ["authenticate_attempt_successful", "challenge_required"]

        if status in approved_list:
            result_category = "🟢 VBV Approved"
        elif status in not_approved_list:
            result_category = "🔴 VBV Not Approved"
        elif status in attempted_list:
            result_category = "🟡 VBV Attempted"
        else:
            result_category = "⚫ Non-VBV"

        # Fetch BIN info from HandyAPI via bin_handler
        try:
            from handlers.bin_handler import lookup_bin
            cc_number = card_input.split("|")[0] if "|" in card_input else card_input
            bin_info = await lookup_bin(cc_number)
            if bin_info and "error" not in bin_info:
                bin_data = {
                    "bin": bin_info.get("bin", "N/A"),
                    "scheme": bin_info.get("scheme", "N/A"),
                    "type": bin_info.get("type", "N/A"),
                    "bank": bin_info.get("bank", "N/A"),
                    "country": bin_info.get("country", "N/A"),
                    "emoji": bin_info.get("flag", "")
                }
            else:
                bin_data = {
                    "bin": cc_number[:6],
                    "scheme": "N/A",
                    "type": "N/A",
                    "bank": "N/A",
                    "country": "N/A",
                    "emoji": ""
                }
        except Exception as bin_err:
            print(f"Error fetching BIN in fetch_vbv_status: {bin_err}")
            bin_data = {
                "bin": card_input[:6],
                "scheme": "N/A",
                "type": "N/A",
                "bank": "N/A",
                "country": "N/A",
                "emoji": ""
            }

        return {
            "success": True,
            "category": result_category,
            "raw_status": result_val,
            "details": details,
            "data": bin_data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_cards(text):
    """Extract cards from text using regex."""
    return re.findall(r'(\d{13,19})[|](\d{1,2})[|](\d{2,4})[|](\d{3,4})', text)

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("vbv")
    async def handle_vbv(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "VBV"):
            return

        # Extract cards from message or reply
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await bot.reply_to(message, f"❌ Card details missing! Usage: `{command_prefixes_list[0]}vbv card|month|year|cvv`", parse_mode="Markdown")
            return

        card_tuple = found_cards[0]
        card_input = "|".join(card_tuple)
        
        processing_msg = await bot.reply_to(message, "🔍 Checking VBV status...")

        result = await fetch_vbv_status(card_input)
        
        if not result["success"]:
            await bot.edit_message_text(f"❌ {result['error']}", message.chat.id, processing_msg.message_id)
            return

        data = result["data"]
        details = result.get("details", {})
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

        enrolled_val = details.get("enrolled")
        enrolled_str = "Yes" if enrolled_val == "Y" else "No" if enrolled_val == "N" else str(enrolled_val or "N/A")
        liability_val = details.get("liability_shifted")
        liability_str = "Yes" if liability_val is True else "No" if liability_val is False else str(liability_val or "N/A")

        res_text = (
            f"𝗖𝗮𝗿𝗱: <code>{card_input}</code>\n"
            f"𝗦𝘁𝗮𝘁𝘂𝘀: {result['category']}\n"
            f"<b>𝗥𝗲𝘀𝘂𝗹𝘁:</b> {html.escape(result['raw_status'])}\n"
            f"<b>𝗘𝗻𝗿𝗼𝗹𝗹𝗲𝗱:</b> {enrolled_str} | <b>𝗟𝗶𝗮𝗯𝗶𝗹𝗶𝘁𝘆 𝗦𝗵𝗶𝗳𝘁:</b> {liability_str}\n\n"
            f"•━━━━━ 𝗕𝗶𝗻 𝗜𝗻𝗳𝗼 ━━━━━•\n"
            f" 𝗕𝗜𝗡: <code>{data.get('bin', 'N/A')}</code>\n"
            f"𝗕𝗿𝗮𝗻𝗱: {data.get('scheme', 'N/A')}\n"
            f"𝗧𝘆𝗽𝗲: {data.get('type', 'N/A')}\n"
            f"𝗕𝗮𝗻𝗸: {data.get('bank', 'N/A')}\n"
            f"𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {data.get('country', 'N/A')} {data.get('emoji', '')}\n"
            f"•━━━━━━━━━━━━━━━━━━•\n\n"
            f"{footer}"
        )

        await bot.edit_message_text(
            res_text,
            message.chat.id,
            processing_msg.message_id,
            parse_mode="HTML"
        )

    @custom_command_handler("mvbv")
    async def handle_mvbv(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "Mass VBV"):
            return

        # Extract cards from message or reply
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_cards = extract_cards(content)
        if not found_cards:
            await bot.reply_to(message, "❌ No valid cards found.")
            return

        # Limit to 15
        cards_to_check = ["|".join(c) for c in found_cards[:15]]
        
        processing_msg = await bot.reply_to(message, f"🔍 <b>Starting VBV Mass Check (0/{len(cards_to_check)})</b>", parse_mode="HTML")
        if not processing_msg:
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}>"

        results = []
        for i, card in enumerate(cards_to_check):
            # 2-4 seconds delay as requested for stability
            import time, random
            time.sleep(random.uniform(2, 4))
            
            res = await fetch_vbv_status(card)
            
            if res["success"]:
                category = res["category"]
                raw_status = res["raw_status"]
            else:
                category = "❌ Error"
                raw_status = res["error"]

            formatted_res = (
                f"•━━━━━ 𝗖𝗮𝗿𝗱 {i+1} ━━━━━•\n"
                f"𝗖𝗮𝗿𝗱: <code>{card}</code>\n"
                f"𝗦𝘁𝗮𝘁𝘂𝘀: {category}\n"
                f"𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {html.escape(raw_status)}"
            )
            results.append(formatted_res)

            progress = f"🔄 <b>𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:</b> {i+1}/{len(cards_to_check)}...\n\n"
            reply_text = progress + "\n\n".join(results) + "\n\n" + footer
            
            if i < len(cards_to_check) - 1: # Don't edit logic for the very last one here
                try:
                    await bot.edit_message_text(reply_text.strip(), message.chat.id, processing_msg.message_id, parse_mode="HTML")
                except:
                    pass

        # Final results
        final_text = "\n\n".join(results) + "\n\n" + footer
        try:
            await bot.edit_message_text(final_text.strip(), message.chat.id, processing_msg.message_id, parse_mode="HTML")
        except:
            pass
