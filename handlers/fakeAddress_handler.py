import requests
from fuzzywuzzy import fuzz
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import asyncio

COUNTRIES_API = "https://fakexy.vercel.app/api/countries"
ADDRESS_API = "https://fakexy.vercel.app/api/address?code="

def _load_countries():
    try:
        response = requests.get(COUNTRIES_API, timeout=15)
        response.raise_for_status()
        data = response.json()
        countries = data.get("countries", {})
        return {code: info["name"] for code, info in countries.items()}
    except Exception as e:
        print(f"[fakeAddress] Failed to load countries from API: {e}. Using fallback.")
        return {
            "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan",
            "AG": "Antigua And Barbuda", "AI": "Anguilla", "AL": "Albania",
            "AM": "Armenia", "AO": "Angola", "AQ": "Antarctica", "AR": "Argentina",
            "AS": "American Samoa", "AT": "Austria", "AU": "Australia", "AW": "Aruba",
            "AX": "Åland Islands", "AZ": "Azerbaijan", "BA": "Bosnia And Herzegovina",
            "BB": "Barbados", "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso",
            "BG": "Bulgaria", "BH": "Bahrain", "BI": "Burundi", "BJ": "Benin",
            "BL": "Saint Barthelemy", "BM": "Bermuda", "BN": "Brunei Darussalam",
            "BO": "Bolivia", "BQ": "Bonaire, Sint Eustatius And Saba", "BR": "Brazil",
            "BS": "Bahamas", "BT": "Bhutan", "BV": "Bouvet Island", "BW": "Botswana",
            "BY": "Belarus", "BZ": "Belize", "CA": "Canada", "CC": "Cocos (Keeling) Islands",
            "CD": "Democratic Republic Of The Congo", "CF": "Central African Republic",
            "CG": "Republic Of The Congo", "CH": "Switzerland", "CI": "Côte D'Ivoire",
            "CK": "Cook Islands", "CL": "Chile", "CM": "Cameroon", "CN": "China",
            "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba", "CV": "Cabo Verde",
            "CW": "Curaçao", "CX": "Christmas Island", "CY": "Cyprus",
            "CZ": "Czech Republic", "DE": "Germany", "DJ": "Djibouti", "DK": "Denmark",
            "DM": "Dominica", "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador",
            "EE": "Estonia", "EG": "Egypt", "EH": "Western Sahara", "ER": "Eritrea",
            "ES": "Spain", "ET": "Ethiopia", "FI": "Finland", "FJ": "Fiji",
            "FK": "Falkland Islands (Malvinas)", "FM": "Federated States Of Micronesia",
            "FO": "Faroe Islands", "FR": "France", "GA": "Gabon", "GB": "United Kingdom",
            "GD": "Grenada", "GE": "Georgia", "GF": "French Guiana", "GG": "Guernsey",
            "GH": "Ghana", "GI": "Gibraltar", "GL": "Greenland", "GM": "Gambia",
            "GN": "Guinea", "GP": "Guadeloupe", "GQ": "Equatorial Guinea", "GR": "Greece",
            "GS": "South Georgia And The South Sandwich Islands", "GT": "Guatemala",
            "GU": "Guam", "GW": "Guinea-Bissau", "GY": "Guyana", "HK": "Hong Kong",
            "HM": "Heard And Mcdonald Islands", "HN": "Honduras", "HR": "Croatia",
            "HT": "Haiti", "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland",
            "IL": "Israel", "IM": "Isle Of Man", "IN": "India",
            "IO": "British Indian Ocean Territory", "IQ": "Iraq", "IR": "Iran",
            "IS": "Iceland", "IT": "Italy", "JE": "Jersey", "JM": "Jamaica",
            "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan",
            "KH": "Cambodia", "KI": "Kiribati", "KM": "Comoros",
            "KN": "Saint Kitts And Nevis", "KP": "North Korea", "KR": "South Korea",
            "KW": "Kuwait", "KY": "Cayman Islands", "KZ": "Kazakhstan",
            "LA": "Lao People'S Democratic Republic", "LB": "Lebanon", "LC": "Saint Lucia",
            "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Liberia", "LS": "Lesotho",
            "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya",
            "MA": "Morocco", "MC": "Monaco", "MD": "Republic Of Moldova", "ME": "Montenegro",
            "MF": "Saint Martin", "MG": "Madagascar", "MH": "Marshall Islands",
            "MK": "North Macedonia", "ML": "Mali", "MM": "Myanmar", "MN": "Mongolia",
            "MO": "Macao", "MP": "Northern Mariana Islands", "MQ": "Martinique",
            "MR": "Mauritania", "MS": "Montserrat", "MT": "Malta", "MU": "Mauritius",
            "MV": "Maldives", "MW": "Malawi", "MX": "Mexico", "MY": "Malaysia",
            "MZ": "Mozambique", "NA": "Namibia", "NC": "New Caledonia", "NE": "Niger",
            "NF": "Norfolk Island", "NG": "Nigeria", "NI": "Nicaragua",
            "NL": "Netherlands", "NO": "Norway", "NP": "Nepal", "NR": "Nauru",
            "NU": "Niue", "NZ": "New Zealand", "OM": "Oman", "PA": "Panama",
            "PE": "Peru", "PF": "French Polynesia", "PG": "Papua New Guinea",
            "PH": "Philippines", "PK": "Pakistan", "PL": "Poland",
            "PM": "Saint Pierre And Miquelon", "PN": "Pitcairn Islands", "PR": "Puerto Rico",
            "PS": "Palestinian Territory", "PT": "Portugal", "PW": "Palau",
            "PY": "Paraguay", "QA": "Qatar", "RE": "Reunion", "RO": "Romania",
            "RS": "Republic Of Serbia", "RU": "Russian Federation", "RW": "Rwanda",
            "SA": "Saudi Arabia", "SB": "Solomon Islands", "SC": "Seychelles",
            "SD": "Sudan", "SE": "Sweden", "SG": "Republic Of Singapore",
            "SH": "Saint Helena", "SI": "Slovenia", "SJ": "Svalbard And Jan Mayen Islands",
            "SK": "Slovakia", "SL": "Sierra Leone", "SM": "San Marino", "SN": "Senegal",
            "SO": "Somalia", "SR": "Suriname", "SS": "South Sudan",
            "ST": "São Tomé And Príncipe", "SV": "El Salvador", "SX": "Sint Maarten",
            "SY": "Syrian Arab Republic", "SZ": "Eswatini",
            "TC": "Turks And Caicos Islands", "TD": "Chad",
            "TF": "French Southern Territories", "TG": "Togo", "TH": "Thailand",
            "TJ": "Tajikistan", "TK": "Tokelau", "TL": "Timor-Leste",
            "TM": "Turkmenistan", "TN": "Tunisia", "TO": "Tonga", "TR": "Turkey",
            "TT": "Trinidad And Tobago", "TV": "Tuvalu", "TW": "Taiwan",
            "TZ": "Tanzania (United Republic)", "UA": "Ukraine", "UG": "Uganda",
            "UM": "United States Minor Outlying Islands", "US": "United States",
            "UY": "Uruguay", "UZ": "Uzbekistan", "VA": "Vatican City State",
            "VC": "Saint Vincent And The Grenadines", "VE": "Venezuela",
            "VG": "Virgin Islands (British)", "VI": "United States Virgin Islands",
            "VN": "Vietnam", "VU": "Vanuatu", "WF": "Wallis And Futuna Islands",
            "WS": "Samoa", "XK": "Kosovo", "YE": "Yemen", "YT": "Mayotte",
            "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe",
        }

code_to_name = _load_countries()

def _build_lookup():
    lookup = {name.lower(): code for code, name in code_to_name.items()}
    lookup.update({code.lower(): code for code in code_to_name.keys()})
    lookup.update({
        'uk': 'GB',
        'great britain': 'GB',
        'great britain (uk)': 'GB',
        'united kingdom (uk)': 'GB',
        'kzt': 'KZ',
    })
    return lookup

country_lookup = _build_lookup()

def find_country(input_text: str):
    input_lower = input_text.strip().lower()
    if input_lower in country_lookup:
        code = country_lookup[input_lower]
        return code, code_to_name.get(code)

    suggestions = []
    best_match = None
    best_score = 0
    for name_lower, code in country_lookup.items():
        if len(name_lower) == 2:
            continue
        ratio = fuzz.ratio(input_lower, name_lower)
        partial_ratio = fuzz.partial_ratio(input_lower, name_lower)
        if partial_ratio == 100:
            best_match = code
            break
        if ratio >= 80 or (len(input_lower) > 2 and partial_ratio >= 90):
            if ratio > best_score:
                best_score = ratio
                best_match = code
            suggestions.append(f"{code_to_name.get(code)} ({code})")

    if best_match and best_score >= 80:
        return best_match, code_to_name.get(best_match)

    suggestions = sorted(list(set(suggestions)))
    return None, suggestions if suggestions else None

def get_address_caption(address, username):
    footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

    flag = address.get('Flag Emoji') or address.get('Flag_Emoji', '')
    country_code = (address.get('Country Code') or address.get('Country_Code', '')).upper()
    header = f"<b>{flag} Address for {address.get('Country', 'Unknown')}</b> (<code>{country_code}</code>)\n"
    header += f"•{'━'*10}•\n"

    personal_keys = ["Full Name", "Gender", "Birthday", "Phone Number"]
    additional_candidate_keys = ["Time Zone", "Timezone", "Currency", "currency"]
    static_keys = set(personal_keys + additional_candidate_keys + [
        "Country_Flag", "Country Flag", "Flag Emoji", "Flag_Emoji",
        "Country", "Country Code", "Country_Code"
    ])

    personal_info = ""
    for key in personal_keys:
        if key in address:
            personal_info += f"<b>{key}</b>: <code>{address[key]}</code>\n"

    additional_info = ""
    if "Time Zone" in address or "Timezone" in address:
        val = address.get("Time Zone") or address.get("Timezone")
        additional_info += f"<b>Time Zone</b>: <code>{val}</code>\n"
    if "Currency" in address or "currency" in address:
        val = address.get("Currency") or address.get("currency")
        additional_info += f"<b>Currency</b>: <code>{val}</code>\n"

    address_info = ""
    for key, value in address.items():
        if key not in static_keys:
            address_info += f"<b>{key}</b>: <code>{value}</code>\n"

    caption = header
    if personal_info:
        caption += personal_info

    if address_info:
        caption += f"•{'━'*5} 𝗔𝗱𝗱𝗿𝗲𝘀𝘀 {'━'*5}•\n"
        caption += address_info

    if additional_info:
        caption += f"•{'━'*5} 𝗔𝗱𝗱𝗶𝘁𝗶𝗼𝗻𝗮𝗹 𝗜𝗻𝗳𝗼 {'━'*5}•\n"
        caption += additional_info

    return f"{caption}\n{footer}"

def get_regen_markup(query, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("♻️ Regenerate", callback_data=f"regen_fake:{query}:{user_id}"))
    return markup

def get_country_keyboard(page, user_id):
    sorted_countries = sorted(code_to_name.items(), key=lambda x: x[1])
    per_page = 20
    total_pages = (len(sorted_countries) + per_page - 1) // per_page

    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(sorted_countries))
    page_items = sorted_countries[start_idx:end_idx]

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for code, name in page_items:
        buttons.append(InlineKeyboardButton(name, callback_data=f"set_fake:{code}:{user_id}"))

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_fake:{page-1}:{user_id}"))

    nav_buttons.append(InlineKeyboardButton(f"Page {page+1}/{total_pages}", callback_data="none"))

    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_fake:{page+1}:{user_id}"))

    markup.row(*nav_buttons)
    return markup

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @bot.callback_query_handler(func=lambda call: call.data.startswith("page_fake:"))
    async def callback_page_fake(call):
        parts = call.data.split(":")
        page = int(parts[1])
        original_user_id = parts[2]

        if str(call.from_user.id) != str(original_user_id):
            await bot.answer_callback_query(call.id, "❌ Only the original requester can navigate.", show_alert=True)
            return

        markup = get_country_keyboard(page, original_user_id)
        await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_fake:"))
    async def callback_set_fake(call):
        parts = call.data.split(":")
        code = parts[1]
        original_user_id = parts[2]

        if str(call.from_user.id) != str(original_user_id):
            await bot.answer_callback_query(call.id, "❌ Only the original requester can select a country.", show_alert=True)
            return

        await bot.answer_callback_query(call.id, f"🌐 Selected {code_to_name.get(code, code)}")
        loading_msg = await bot.send_message(call.message.chat.id, "⏳ <b>Generating address...</b>", parse_mode="HTML")

        try:
            response = await asyncio.to_thread(requests.get, f"{ADDRESS_API}{code}", timeout=30)
            response.raise_for_status()
            address = response.json()

            if not address:
                await bot.edit_message_text(
                    f"❌ No address data found for <code>{code_to_name.get(code)}</code>.",
                    chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode="HTML"
                )
                return

            username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
            caption_text = get_address_caption(address, username)
            markup = get_regen_markup(code, original_user_id)

            flag_url = address.get('Country Flag') or address.get('Country_Flag')
            if flag_url:
                await bot.send_photo(call.message.chat.id, flag_url, caption=caption_text, parse_mode="HTML", reply_markup=markup)
                await bot.delete_message(call.message.chat.id, loading_msg.message_id)
            else:
                await bot.edit_message_text(caption_text, chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode="HTML", reply_markup=markup)

        except Exception as e:
            await bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=call.message.chat.id, message_id=loading_msg.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("regen_fake:"))
    async def callback_regen_fake(call):
        parts = call.data.split(":")
        query = parts[1]
        original_user_id = parts[2]

        if str(call.from_user.id) != str(original_user_id):
            await bot.answer_callback_query(call.id, "❌ Only the original requester can regenerate this.", show_alert=True)
            return

        try:
            await bot.answer_callback_query(call.id, "♻ Generating new address...")
            response = await asyncio.to_thread(requests.get, f"{ADDRESS_API}{query}", timeout=30)
            response.raise_for_status()
            address = response.json()

            if not address:
                await bot.answer_callback_query(call.id, "❌ No data found.", show_alert=True)
                return

            username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
            caption = get_address_caption(address, username)
            markup = get_regen_markup(query, original_user_id)

            flag_url = address.get('Country Flag') or address.get('Country_Flag')
            if flag_url:
                if call.message.photo:
                    await bot.edit_message_media(
                        media=InputMediaPhoto(flag_url, caption=caption, parse_mode="HTML"),
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=markup
                    )
                else:
                    await bot.send_photo(call.message.chat.id, flag_url, caption=caption, parse_mode="HTML", reply_markup=markup)
                    await bot.delete_message(call.message.chat.id, call.message.message_id)
            else:
                await bot.edit_message_text(
                    text=caption,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML",
                    reply_markup=markup
                )
        except Exception as e:
            await bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)

    @custom_command_handler("fake")
    async def handle_fake(message):
        if check_usage_limit and not await check_usage_limit(message, "Fake Address"):
            return

        cmd_parts = message.text.split(" ", 1)
        user_input = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

        if not user_input:
            await bot.reply_to(
                message,
                f"❌ Country name or code missing.\n\nExample:\n<code>{command_prefixes_list[0]}fake US</code>\n<code>{command_prefixes_list[0]}fake bangladesh</code>",
                parse_mode="HTML"
            )
            return

        loading_msg = await bot.send_message(message.chat.id, "⏳ <b>Generating address...</b>", parse_mode="HTML")

        try:
            code, name = find_country(user_input)
            if not code:
                if isinstance(name, list):
                    suggestions = "\n".join([f"• {s}" for s in name[:10]])
                    await bot.edit_message_text(
                        f"❌ Country not found. Did you mean:\n{suggestions}",
                        chat_id=message.chat.id, message_id=loading_msg.message_id
                    )
                else:
                    await bot.edit_message_text(
                        f"❌ Country <code>{user_input}</code> not found.",
                        chat_id=message.chat.id, message_id=loading_msg.message_id, parse_mode="HTML"
                    )
                return

            response = await asyncio.to_thread(requests.get, f"{ADDRESS_API}{code}", timeout=30)
            response.raise_for_status()
            address = response.json()

            if not address:
                await bot.edit_message_text(
                    f"❌ No address data found for <code>{name}</code>.",
                    chat_id=message.chat.id, message_id=loading_msg.message_id, parse_mode="HTML"
                )
                return

            username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            caption_text = get_address_caption(address, username)
            markup = get_regen_markup(code, message.from_user.id)

            flag_url = address.get('Country Flag') or address.get('Country_Flag')
            if flag_url:
                await bot.send_photo(message.chat.id, flag_url, caption=caption_text, parse_mode="HTML", reply_markup=markup)
                await bot.delete_message(message.chat.id, loading_msg.message_id)
            else:
                await bot.edit_message_text(caption_text, chat_id=message.chat.id, message_id=loading_msg.message_id, parse_mode="HTML", reply_markup=markup)

        except Exception as e:
            await bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=message.chat.id, message_id=loading_msg.message_id)

    @custom_command_handler("country")
    async def handle_countries(message):
        markup = get_country_keyboard(0, message.from_user.id)
        msg = (
            f"<b>🌐 Supported Countries (Total: {len(code_to_name)})</b>\n"
            f"{'━'*20}\n"
            "Select a country below to generate a fake address."
        )
        await bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)