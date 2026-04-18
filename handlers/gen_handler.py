import requests
import re
import base64
from telebot import types
from telebot.types import Message, CallbackQuery
import io
import asyncio

def encode_data(data: str) -> str:
    return base64.urlsafe_b64encode(data.encode()).decode()

def decode_data(encoded: str) -> str:
    return base64.urlsafe_b64decode(encoded.encode()).decode()

async def generate_cards_via_api(bin_input, count, month=None, year=None, cvv=None):
    params = {
        "bin": bin_input,
        "limit": count
    }
    if month:
        params["month"] = month
    if year:
        params["year"] = year
    if cvv:
        params["cvv"] = cvv

    try:
        url = "https://cc-gen-eight.vercel.app/generate"
        response = await asyncio.to_thread(requests.get, url, params=params)
        if response.status_code == 200:
            data = response.json()
            cards = []
            for card in data.get("cards", []):
                card_number = card.get("number")
                expiry = card.get("expiry")
                cvv_code = card.get("cvv")
                cards.append(f"{card_number}|{expiry.replace('/', '|')}|{cvv_code}")

            bin_info = data.get("bin_info", None)
            return {
                "cards": cards,
                "info": {
                    "brand": bin_info.get("scheme", "N/A").upper() if bin_info else "N/A",
                    "type": bin_info.get("type", "N/A").upper() if bin_info else "N/A",
                    "level": bin_info.get("tier", "N/A").upper() if bin_info else "N/A",
                    "bank": bin_info.get("bank", "N/A") if bin_info else "N/A",
                    "country": bin_info.get("country", "N/A") if bin_info else "",
                    "flag": bin_info.get("flag", "") if bin_info else "",
                }
            }
        elif response.status_code == 400:
            error_data = response.json()
            print(f"API Error (400): {error_data.get('message', 'Unknown error')}")
            return {"error": error_data.get("message", "Invalid BIN or parameters.")}
        else:
            print(f"API request failed with status code: {response.status_code}")
            return {"error": f"API request failed with status code: {response.status_code}"}

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return {"error": f"Network error or API is down: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": f"An unexpected error occurred: {e}"}

def create_text_file(cards):
    file_content = "\n".join(cards)
    file_obj = io.BytesIO(file_content.encode())
    file_obj.name = "generated_cards.txt"
    return file_obj

def extract_bin_from_text(text: str):
    bin_part = None
    month = None
    year = None
    cvv = None

    full_format_match = re.search(
        r'(\d{6,16}(?:x{0,10}|X{0,10})?)\s*[|/]?\s*(\d{1,2})?\s*[|/]?\s*(\d{2,4})?\s*[|/]?\s*(\d{3,4}|rnd)?',
        text, re.IGNORECASE
    )
    if full_format_match:
        extracted_bin = full_format_match.group(1)
        bin_part = re.match(r'^\d+', extracted_bin).group(0) if re.match(r'^\d+', extracted_bin) else None

        month = full_format_match.group(2)
        year = full_format_match.group(3)
        cvv = full_format_match.group(4)

        if month and len(month) == 1:
            month = '0' + month
        if year and len(year) == 2:
            current_year_prefix = 20 if int(year) < 50 else 19
            year = str(current_year_prefix) + year
        if cvv and cvv.lower() == 'rnd':
            cvv = None

        if bin_part:
            return bin_part, month, year, cvv

    bin_patterns = [
        r'\b(?:BIN|Bin|𝗕𝗶𝗻|💳|B\s?I\s?N)\s*[:]?\s*(\d{6,16}(?:x{0,10}|X{0,10})?)\b',
        r'\b(\d{15,16}(?:x{0,10}|X{0,10})?)\b',
        r'\b(\d{6,10}(?:x{0,10}|X{0,10})?)\s*\|\d{1,2}\|\d{2,4}\b'
    ]
    for pattern in bin_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted_bin = match.group(1)
            bin_part = re.match(r'^\d+', extracted_bin).group(0)
            break

    # Month/Year patterns
    month_year_patterns = [
        r'\b(?:Fecha|🗓|𝗙𝗲𝗰𝗵𝗮|Date|Exp|Expiry)\s*[:]?\s*(\d{1,2})[/\s|-](\d{2,4})\b',
        r'\b(\d{1,2})[/\s|-](\d{2,4})\b'
    ]
    for pattern in month_year_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            month = match.group(1)
            year = match.group(2)
            if len(month) == 1:
                month = '0' + month
            if len(year) == 2:
                current_year_prefix = 20 if int(year) < 50 else 19
                year = str(current_year_prefix) + year
            break

    # CVV patterns
    cvv_patterns = [
        r'\b(?:CVV|Cvv|𝗖𝘃𝘃)\s*[:]?\s*(\d{3,4}|rnd)\b',
        r'\b(\d{3,4}|rnd)\b(?=\s*$|\s*[.,;])'
    ]
    for pattern in cvv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            cvv_val = match.group(1)
            if cvv_val.lower() != 'rnd':
                cvv = cvv_val
            break

    return bin_part, month, year, cvv

def get_user_identifier(user):
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        return user.first_name
    elif user.last_name:
        return user.last_name
    else:
        return str(user.id)


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("gen")
    async def handle_gen(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "Gen"):
            return
        try:
            bin_part = None
            month = None
            year = None
            cvv = None
            count = 10

            parts_split = message.text.strip().split()
            if len(parts_split) > 1:
                full_input_after_command = " ".join(parts_split[1:])
            else:
                full_input_after_command = ""

            if message.reply_to_message:
                replied_text = message.reply_to_message.text or message.reply_to_message.caption
                if replied_text:
                    bin_part, month, year, cvv = extract_bin_from_text(replied_text)

                    if full_input_after_command and full_input_after_command.isdigit():
                        count = int(full_input_after_command)
                        count = min(count, 1000)
                    elif not bin_part:
                        await bot.reply_to(message, "❌ Sorry! No valid BIN found from replied message.", parse_mode="Markdown")
                        return
                else:
                    await bot.reply_to(message, "❌ No text or caption in replied message to extract BIN.", parse_mode="Markdown")
                    return
            else:
                if not full_input_after_command:
                    await bot.reply_to(message, f"❌ BIN missing. Example: `{command_prefixes_list[0]}gen 515462xxxxxx|02|28|573 5` or `{command_prefixes_list[1]}gen 515462xxxxxx|02|28|573 5`", parse_mode="Markdown")
                    return

                full_input = full_input_after_command
                parts = full_input.split()

                if len(parts) > 1 and parts[-1].isdigit():
                    count = int(parts[-1])
                    count = min(count, 1000)
                    base_input = " ".join(parts[:-1]).strip()
                else:
                    base_input = full_input

                input_parts_cc = re.split(r"[|/]", base_input)
                bin_part = input_parts_cc[0]
                month = input_parts_cc[1] if len(input_parts_cc) > 1 else None
                year = input_parts_cc[2] if len(input_parts_cc) > 2 else None
                cvv = input_parts_cc[3] if len(input_parts_cc) > 3 else None

                if month and len(month) == 1:
                    month = '0' + month
                if year and len(year) == 2:
                    current_year_prefix = 20 if int(year) < 50 else 19
                    year = str(current_year_prefix) + year

            if not bin_part:
                await bot.reply_to(message, "❌ BIN not found. Please check your input or replied message.", parse_mode="Markdown")
                return

            result = await generate_cards_via_api(bin_part, count, month, year, cvv)

            if result and "error" in result:
                await bot.reply_to(message, f"❌ Card generation failed: {result['error']}")
                return
            elif not result or not result.get("cards"):
                await bot.reply_to(message, "❌ Card generation failed. API may be down or input invalid.")
                return

            cards = result["cards"]
            info = result.get("info")

            requester_info = get_user_identifier(message.from_user)


            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

            if count > 10:
                file = create_text_file(cards)
                caption = (
                    f"𝗕𝗜𝗡 ⇾ <code>{bin_part}</code>\n"
                    f"𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ {count}\n"
                    f"\n{footer}"
                )
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=file,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                msg = (
                    f"𝗕𝗜𝗡 ⇾ <code>{bin_part}</code>\n"
                    f"𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ {count}\n\n"
                    f"•──────────────────────•\n"
                    + "\n".join([f"<code>{card}</code>" for card in cards]) +
                    f"\n•──────────────────────•\n"
                )
                if info:
                    msg += (
                        f"<b>𝗜𝗻𝗳𝗼:</b> {info['brand']} - {info['type']} - {info['level']}\n"
                        f"<b>𝗕𝗮𝗻𝗸:</b> {info['bank']}\n"
                        f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {info['country']} {info['flag']}\n\n"
                    )

                regen_input_data = f"{bin_part}"
                if month:
                    regen_input_data += f"|{month}"
                if year:
                    regen_input_data += f"|{year}"
                if cvv:
                    regen_input_data += f"|{cvv}"
                regen_input_data += f" {count}"

                msg += footer
                encoded_input = encode_data(regen_input_data)
                cb_data = f"regen|{encoded_input}|{message.from_user.id}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("♻️ Regenerate", callback_data=cb_data),
                           types.InlineKeyboardButton("📄 Copy", callback_data="copy_cards"))
                await bot.reply_to(message, msg, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            await bot.reply_to(message, f"❌ Error: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("regen|"))
    async def handle_regen(call: CallbackQuery):
        try:
            parts = call.data.split('|')
            encoded_input = parts[1]
            original_user_id = parts[2] if len(parts) > 2 else None
            
            if original_user_id and str(call.from_user.id) != str(original_user_id):
                await bot.answer_callback_query(call.id, "❌ You are not the owner of this request.", show_alert=True)
                return

            decoded_input = decode_data(encoded_input)

            parts_with_count = decoded_input.split()
            count = 10
            base_input = decoded_input

            if len(parts_with_count) > 1 and parts_with_count[-1].isdigit():
                count = int(parts_with_count[-1])
                count = min(count, 1000)
                base_input = " ".join(parts_with_count[:-1]).strip()

            parts = re.split(r"[|/]", base_input)
            bin_part = parts[0]
            month = parts[1] if len(parts) > 1 else None
            year = parts[2] if len(parts) > 2 else None
            cvv = parts[3] if len(parts) > 3 else None

            if month and len(month) == 1:
                month = '0' + month
            if year and len(year) == 2:
                current_year_prefix = 20 if int(year) < 50 else 19
                year = str(current_year_prefix) + year

            result = await generate_cards_via_api(bin_part, count, month, year, cvv)

            if result and "error" in result:
                await bot.answer_callback_query(call.id, f"❌ Re-generation failed: {result['error']}")
                return
            elif not result or not result.get("cards"):
                await bot.answer_callback_query(call.id, "❌ Card re-generation failed.")
                return

            cards = result["cards"]
            info = result.get("info")

            requester_info = get_user_identifier(call.from_user)

            msg = (
                f"𝗕𝗜𝗡 ⇾ <code>{bin_part}</code>\n"
                f"𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ {count}\n\n"
                f"•──────────────────────•\n"
                + "\n".join([f"<code>{card}</code>" for card in cards]) +
                f"\n•──────────────────────•\n"
            )
            if info:
                msg += (
                    f"<b>𝗜𝗻𝗳𝗼:</b> {info['brand']} - {info['type']} - {info['level']}\n"
                    f"<b>𝗕𝗮𝗻𝗸:</b> {info['bank']}\n"
                    f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {info['country']} {info['flag']}\n\n"
                )
            user = call.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"
            msg += footer

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("♻️ Regenerate", callback_data=call.data),
                       types.InlineKeyboardButton("📄 Copy", callback_data="copy_cards"))

            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=msg,
                parse_mode="HTML",
                reply_markup=markup
            )
            await bot.answer_callback_query(call.id, "✅ Cards re-generated.")

        except Exception as e:
            await bot.answer_callback_query(call.id, f"⚠️ Error: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data == "copy_cards")
    async def handle_copy_cards(call: CallbackQuery):
        try:
            text = call.message.text
            cards = re.findall(r'\d{12,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}', text)
            
            if not cards:
                await bot.answer_callback_query(call.id, "❌ No cards found to copy.")
                return

            cards_text = "\n".join(cards)
            response_text = f"<code>{cards_text}</code>"
            
            await bot.send_message(call.message.chat.id, response_text, parse_mode="HTML")
            await bot.answer_callback_query(call.id, "✅ Cards copied!")
            
        except Exception as e:
            await bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
