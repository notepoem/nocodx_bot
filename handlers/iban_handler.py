import requests
import difflib
import pycountry
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
import asyncio


IBAN_GENERATE_API = "https://drlabapis.onrender.com/api/generateiban?country={code}"
IBAN_COUNTRIES_API = "https://drlabapis.onrender.com/api/iban/country"

COUNTRY_FLAGS = {
    country.alpha_2: "".join(chr(0x1F1E6 + ord(c) - ord('A')) for c in country.alpha_2)
    for country in pycountry.countries
    if hasattr(country, "alpha_2")
}

IBAN_ALIASES = {
    "united kingdom": "gb", "gb": "gb", "uk": "gb",
    "kazakhstan": "kz", "kz": "kz", "kzt": "kz",
}

def get_regen_markup(country_code, user_id, showing_details=False):
    markup = InlineKeyboardMarkup()
    detail_btn = InlineKeyboardButton("⬆ Hide Details", callback_data=f"iban_hide:{country_code}:{user_id}") if showing_details else InlineKeyboardButton("📃 Show Details", callback_data=f"iban_show:{country_code}:{user_id}")
    markup.add(
        detail_btn,
        InlineKeyboardButton("♻️ Regenerate", callback_data=f"regen_iban:{country_code}:{user_id}")
    )
    return markup

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    user_iban_data = {}

    @bot.callback_query_handler(func=lambda call: call.data.startswith("regen_iban:"))
    async def callback_regen_iban(call):
        parts = call.data.split(":")
        country_code = parts[1]
        original_user_id = parts[2]
        
        if str(call.from_user.id) != str(original_user_id):
            await bot.answer_callback_query(call.id, "❌ Only the original requester can regenerate this.", show_alert=True)
            return

        try:
            await bot.answer_callback_query(call.id, "♻️ Generating new IBANs...")
            generated_ibans = []
            for _ in range(10):
                r = await asyncio.to_thread(requests.get, IBAN_GENERATE_API.format(code=country_code.upper()), timeout=30)
                r.raise_for_status()
                generated_ibans.append(r.json())

            user_iban_data[call.from_user.id] = generated_ibans

            # Fetch metadata for display
            res = await asyncio.to_thread(requests.get, IBAN_COUNTRIES_API, timeout=30)
            res.raise_for_status()
            countries_data = res.json().get("available_country", {})
            country_name = countries_data.get(country_code.upper(), country_code.upper())
            country_flag = COUNTRY_FLAGS.get(country_code.upper(), "🏳️")

            username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            msg_lines = [
                f"<b>𝗜𝗯𝗮𝗻 ⇾ {country_name} {country_flag}</b>",
                f"<b>𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ {len(generated_ibans)}</b>",
                "•──────────────────────•"
            ]
            msg_lines += [f"<code>{iban['iban']}</code>" for iban in generated_ibans]
            msg_lines += [footer]

            markup = get_regen_markup(country_code, original_user_id)
            await bot.edit_message_text("\n".join(msg_lines), call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

        except Exception as e:
            await bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)

    @custom_command_handler("iban")
    async def handle_iban(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "Iban"):
            return
        parts_split = message.text.strip().split()
        user_input_raw = " ".join(parts_split[1:]).strip() if len(parts_split) > 1 else ""
        if not user_input_raw:
            prefix = command_prefixes_list[0] if command_prefixes_list else "/"
            await bot.reply_to(message, f"❌ Country name/code missing.\n\nTry:\n{prefix}iban DE\n{prefix}iban Germany", parse_mode="HTML")
            return

        user_input = user_input_raw.split()[0].lower()

        try:
            res = await asyncio.to_thread(requests.get, IBAN_COUNTRIES_API, timeout=30)
            res.raise_for_status()
            countries_data = res.json().get("available_country", {})
        except:
            await bot.reply_to(message, "❌ Failed to fetch country data.")
            return

        iban_map = {name.lower(): code.lower() for code, name in countries_data.items()}
        iban_map.update({code.lower(): code.lower() for code in countries_data})
        iban_map.update(IBAN_ALIASES)

        country_code = iban_map.get(user_input)

        if not country_code:
            suggestion = difflib.get_close_matches(user_input, list(iban_map.keys()), n=3)
            if suggestion:
                suggestion_text = "\n".join(f"🔹 <code>{iban_map[s]}</code> → {s.title()}" for s in suggestion)
                await bot.reply_to(message, f"❌ Country not found or unsupported.\n\n<b>👉 Close matches:</b>\n{suggestion_text}\n\n<b>📌 Try:</b> <code>{command_prefixes_list[0]}iban Germany</code>", parse_mode="HTML")
            else:
                await bot.reply_to(message, "❌ Unsupported or invalid country.", parse_mode="HTML")
            return

        generated_ibans = []
        for _ in range(10):
            try:
                r = await asyncio.to_thread(requests.get, IBAN_GENERATE_API.format(code=country_code.upper()), timeout=30)
                r.raise_for_status()
                generated_ibans.append(r.json())
            except:
                await bot.send_message(message.chat.id, "❌ IBAN fetch failed.")
                return

        user_iban_data[message.from_user.id] = generated_ibans

        country_name = countries_data.get(country_code.upper(), country_code.upper())
        country_flag = COUNTRY_FLAGS.get(country_code.upper(), "🏳️")

        username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

        msg_lines = [
            f"<b>𝗜𝗯𝗮𝗻 ⇾ {country_name} {country_flag}</b>",
            f"<b>𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ {len(generated_ibans)}</b>",
            "•──────────────────────•"
        ]
        msg_lines += [f"<code>{iban['iban']}</code>" for iban in generated_ibans]
        msg_lines += [footer]

        markup = get_regen_markup(country_code, message.from_user.id)
        await bot.send_message(message.chat.id, "\n".join(msg_lines), parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("iban_"))
    async def handle_toggle(call: CallbackQuery):
        parts = call.data.split(":")
        action = parts[0]
        country_code = parts[1] if len(parts) > 2 else ""
        original_user_id = parts[2] if len(parts) > 2 else parts[1] if len(parts) > 1 else None

        if original_user_id and str(call.from_user.id) != str(original_user_id):
            await bot.answer_callback_query(call.id, "❌ Only the original requester can use these buttons.", show_alert=True)
            return

        user_id = call.from_user.id
        chat_id = call.message.chat.id
        msg_id = call.message.message_id

        ibans = user_iban_data.get(user_id)
        if not ibans:
            await bot.answer_callback_query(call.id, "❌ Expired or missing IBAN data.")
            return

        # Fetch metadata for display (needed for both views)
        try:
            res = await asyncio.to_thread(requests.get, IBAN_COUNTRIES_API, timeout=30)
            res.raise_for_status()
            countries_data = res.json().get("available_country", {})
            country_name = countries_data.get(country_code.upper(), country_code.upper())
            country_flag = COUNTRY_FLAGS.get(country_code.upper(), "🏳️")
        except:
            country_name = country_code.upper()
            country_flag = "🏳️"

        username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

        if action == "iban_show":
            detail_lines = [
                f"<b>𝗜𝗯𝗮𝗻 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 ⇾ {country_name} {country_flag}</b>",
                "•──────────────────────•"
            ]
            for i, iban in enumerate(ibans):
                detail_lines.append(
                    f"<b>IBAN {i+1}:</b>\n"
                    f"  IBAN: <code>{iban.get('iban')}</code>\n"
                    f"  Code: <code>{iban.get('account_Code')}</code>\n"
                    f"  Bank: <code>{iban.get('bank_name')}</code>\n"
                    f"  BIC: <code>{iban.get('bic')}</code>\n"
                )
            detail_lines.append(footer)
            full_msg = "\n".join(detail_lines)

            markup = get_regen_markup(country_code, original_user_id, showing_details=True)
            await bot.edit_message_text(full_msg, chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

        elif action == "iban_hide":
            msg_lines = [
                f"<b>𝗜𝗯𝗮𝗻 ⇾ {country_name} {country_flag}</b>",
                f"<b>𝗔𝗺𝗼𝘂𝗻𝘁 ⇾ {len(ibans)}</b>",
                "•──────────────────────•"
            ]
            msg_lines += [f"<code>{iban['iban']}</code>" for iban in ibans]
            msg_lines += [footer]

            markup = get_regen_markup(country_code, original_user_id, showing_details=False)
            await bot.edit_message_text("\n".join(msg_lines), chat_id, msg_id, parse_mode="HTML", reply_markup=markup)

    
    @custom_command_handler("ibncntry")
    async def handle_iban_countries(message: Message):
        try:
            res = await asyncio.to_thread(requests.get, IBAN_COUNTRIES_API)
            res.raise_for_status()
            countries = res.json().get("available_country", {})

            if not countries:
                await bot.send_message(message.chat.id, "⚠️ কোনো দেশ পাওয়া যায়নি।")
                return

            country_lines = []
            for code, name in sorted(countries.items(), key=lambda x: x[1]):
                flag = COUNTRY_FLAGS.get(code, "🏳️")
                country_lines.append(f"• {name} (<code>{code}</code>) {flag}")

            msg = (
                f"<b>🌍 Supported IBAN Countries (Total: {len(countries)})</b>\n"
                + "\n".join(country_lines) +
                "\n\n<b>📌 Example:</b> <code>/iban Germany</code> বা <code>/iban DE</code>"
            )

            await bot.send_message(message.chat.id, msg, parse_mode="HTML")

        except Exception as e:
            await bot.send_message(message.chat.id, f"❌ Problem loading country list:\n{str(e)}")