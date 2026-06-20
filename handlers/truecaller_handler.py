import requests
import asyncio
import time
from urllib.parse import quote

SUPABASE_URL = "https://ivceekepvezxrewkixrc.supabase.co/functions/v1/lookup-number"
SUPABASE_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2Y2Vla2VwdmV6eHJld2tpeHJjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0NTY2NDksImV4cCI6MjA5MTAzMjY0OX0.8jEYLCSJ5O7jL4e2MM5r4utKrogfVvyWvq4JmI-KO00"

SUPABASE_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.6",
    "apikey": SUPABASE_TOKEN,
    "authorization": f"Bearer {SUPABASE_TOKEN}",
    "content-type": "application/json",
    "origin": "https://seecaller.pro.bd",
    "referer": "https://seecaller.pro.bd/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "x-client-info": "supabase-js-web/2.103.0",
}


def call_main_api(phone_number):
    url = f"https://api.eyecon-app.com/app/getnames.jsp?cli={quote(phone_number)}&lang=en&is_callerid=true&is_ic=true&cv=vc_672_vn_4.2025.10.17.1932_a&requestApi=URLconnection&source=MenifaFragment"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
        'Connection': 'Keep-Alive',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'e-auth-v': 'e1',
        'e-auth': 'a3103057-4728-4242-80d5-d25012410732',
        'e-auth-c': '39',
        'e-auth-k': 'PgdtSBeR0MumR7fO',
        'accept-charset': 'UTF-8',
        'content-type': 'application/x-www-form-urlencoded; charset=utf-8',
    }
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        data = r.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
    return None


def call_fallback_api(phone_number):
    payload = {
        "number": phone_number,
        "_ts": int(time.time() * 1000),
    }
    r = requests.post(SUPABASE_URL, headers=SUPABASE_HEADERS, json=payload, timeout=15)
    if r.status_code == 200:
        result = r.json()
        data = result.get("data")
        if data and data.get("name"):
            return data
    return None


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @custom_command_handler("truecaller", "tc")
    async def handle_truecaller(message):
        if check_usage_limit and not await check_usage_limit(message, "Truecaller"):
            return

        parts_split = message.text.strip().split()
        phone_number = " ".join(parts_split[1:]).strip() if len(parts_split) > 1 else ""

        if phone_number:
            phone_number = phone_number.replace(" ", "").replace("-", "")
            if not phone_number.startswith("+"):
                phone_number = "+" + phone_number

        if not phone_number:
            await bot.reply_to(
                message,
                f"<b>❌ Missing Phone Number!</b>\n\nUsage: <code>{parts_split[0]} +8801234567890</code>",
                parse_mode="HTML"
            )
            return

        processing_msg = await bot.reply_to(message, "<b>🔍 Searching Cloud Databases...</b>", parse_mode="HTML")

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n<b>𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆:</b> {username}"

        try:
            main_result = await asyncio.to_thread(call_main_api, phone_number)

            if main_result:
                name = main_result.get("name", "Unknown")
                info_type = main_result.get("type", "N/A")

                result_text = (
                    f"✨ <b>𝗣𝗵𝗼𝗻𝗲 𝗜𝗱𝗲𝗻𝘁𝗶𝘁𝘆 𝗥𝗲𝘃𝗲𝗮𝗹𝗲𝗱</b> ✨\n"
                    f"•──────────────────────•\n\n"
                    f"👤 <b>𝗡𝗮𝗺𝗲:</b> <code>{name}</code>\n"
                    f"📱 <b>𝗡𝘂𝗺𝗯𝗲𝗿:</b> <code>{phone_number}</code>\n"
                    f"🏷 <b>𝗧𝘆𝗽𝗲:</b> <code>{info_type}</code>\n\n"
                    f"{footer}"
                )
                await bot.edit_message_text(
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id,
                    text=result_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                return

            await bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text="<b>🔍 Trying alternate database...</b>",
                parse_mode="HTML"
            )

            fallback_result = await asyncio.to_thread(call_fallback_api, phone_number)

            if fallback_result:
                name    = fallback_result.get("name", "Unknown")
                carrier = fallback_result.get("carrier") or "N/A"
                country = fallback_result.get("country") or "N/A"
                ftype   = fallback_result.get("type") or "N/A"

                result_text = (
                    f"✨ <b>𝗣𝗵𝗼𝗻𝗲 𝗜𝗱𝗲𝗻𝘁𝗶𝘁𝘆 𝗥𝗲𝘃𝗲𝗮𝗹𝗲𝗱</b> ✨\n"
                    f"•──────────────────────•\n\n"
                    f"👤 <b>𝗡𝗮𝗺𝗲:</b> <code>{name}</code>\n"
                    f"📱 <b>𝗡𝘂𝗺𝗯𝗲𝗿:</b> <code>{phone_number}</code>\n"
                    f"🌐 <b>𝗖𝗮𝗿𝗿𝗶𝗲𝗿:</b> <code>{carrier}</code>\n"
                    f"🗺 <b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> {country}\n"
                    f"🏷 <b>𝗧𝘆𝗽𝗲:</b> <code>{ftype}</code>\n\n"
                    f"{footer}"
                )
                await bot.edit_message_text(
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id,
                    text=result_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                return

            not_found_text = (
                f"❌ <b>𝗡𝗼 𝗗𝗮𝘁𝗮 𝗙𝗼𝘂𝗻𝗱</b>\n"
                f"•──────────────────────•\n\n"
                f"📱 <b>𝗡𝘂𝗺𝗯𝗲𝗿:</b> <code>{phone_number}</code>\n"
                f"⚠️ No matching records found in any database.\n\n"
                f"{footer}"
            )
            await bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text=not_found_text,
                parse_mode="HTML"
            )

        except Exception as e:
            await bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text=f"<b>❌ System Error</b>\n\n<code>{str(e)}</code>",
                parse_mode="HTML"
            )
