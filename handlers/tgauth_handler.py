import requests
from bs4 import BeautifulSoup
import random
import string
from telebot import types
import asyncio

# auth_sessions[user_id] = {
#   'state': 'waiting_phone' | 'waiting_code',
#   'session': requests.Session,   # set after phone step
#   'phone': str,
#   'random_hash': str,
# }
auth_sessions = {}

BASE_HEADERS = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'dnt': '1',
    'origin': 'https://my.telegram.org',
    'referer': 'https://my.telegram.org/auth',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @custom_command_handler("tgauth")
    async def start_auth(message):
        user_id = message.from_user.id
        if check_usage_limit and not await check_usage_limit(message, "TG Auth"):
            return
        auth_sessions[user_id] = {'state': 'waiting_phone'}
        await bot.reply_to(
            message,
            "📱 <b>Telegram API Setup</b>\n\nPlease send your phone number with country code.\nExample: <code>+88017XXXXXXXX</code>",
            parse_mode="HTML"
        )

    @bot.message_handler(func=lambda m: m.from_user.id in auth_sessions and
                         auth_sessions[m.from_user.id].get('state') == 'waiting_phone' and
                         not m.text.startswith('/'))
    async def process_phone_step(message):
        user_id = message.from_user.id
        phone = message.text.strip()

        if not phone.startswith('+'):
            await bot.reply_to(message, "❌ Invalid format. Please include <code>+</code> and country code (e.g., +880...).", parse_mode="HTML")
            return

        s = requests.Session()
        s.headers.update(BASE_HEADERS)
        wait_msg = await bot.reply_to(message, "📡 Sending login request...")

        try:
            r = await asyncio.to_thread(s.post, 'https://my.telegram.org/auth/send_password', data={'phone': phone}, timeout=15)

            if r.status_code != 200:
                await bot.edit_message_text(f"❌ HTTP Error: {r.status_code}\nResponse: {r.text[:200]}", chat_id=message.chat.id, message_id=wait_msg.message_id)
                auth_sessions.pop(user_id, None)
                return

            try:
                response_json = r.json()
            except Exception:
                await bot.edit_message_text("❌ Failed to parse response from Telegram. Please try again.", chat_id=message.chat.id, message_id=wait_msg.message_id)
                auth_sessions.pop(user_id, None)
                return

            random_hash = response_json.get('random_hash')
            if not random_hash:
                error_msg = response_json.get("error", "Failed to get random_hash.")
                await bot.edit_message_text(f"❌ Error: {error_msg}\nCheck if the number is correct.", chat_id=message.chat.id, message_id=wait_msg.message_id)
                auth_sessions.pop(user_id, None)
                return

            auth_sessions[user_id] = {
                'state': 'waiting_code',
                'session': s,
                'phone': phone,
                'random_hash': random_hash
            }

            await bot.edit_message_text(
                "✅ <b>Code Sent!</b>\n\n"
                "Please check your <b>Telegram app</b> (the official one) for a login code and send it here.\n\n"
                "⚠️ <b>Note:</b> The code is <b>CASE-SENSITIVE</b>. Type it exactly as shown.",
                chat_id=message.chat.id,
                message_id=wait_msg.message_id,
                parse_mode="HTML"
            )

        except Exception as e:
            await bot.edit_message_text(f"❌ Exception: {str(e)}", chat_id=message.chat.id, message_id=wait_msg.message_id)
            auth_sessions.pop(user_id, None)

    @bot.message_handler(func=lambda m: m.from_user.id in auth_sessions and
                         auth_sessions[m.from_user.id].get('state') == 'waiting_code' and
                         not m.text.startswith('/'))
    async def process_code_step(message):
        user_id = message.from_user.id
        data = auth_sessions.get(user_id, {})

        if not data:
            await bot.reply_to(message, "❌ Session expired. Please start over with /tgauth.")
            return

        code = message.text.strip()
        s = data['session']
        phone = data['phone']
        random_hash = data['random_hash']

        status_msg = await bot.reply_to(message, "🔄 Logging in...")

        try:
            data_login = {'phone': phone, 'random_hash': random_hash, 'password': code}
            r = await asyncio.to_thread(s.post, 'https://my.telegram.org/auth/login', data=data_login, timeout=15)

            if r.status_code != 200:
                await bot.edit_message_text(f"❌ Login HTTP Error: {r.status_code}", chat_id=message.chat.id, message_id=status_msg.message_id)
                auth_sessions.pop(user_id, None)
                return

            if r.text == 'true':
                s.headers.update({
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-user': '?1',
                    'upgrade-insecure-requests': '1',
                    'referer': 'https://my.telegram.org/',
                })
                s.headers.pop('content-type', None)
                s.headers.pop('x-requested-with', None)
            else:
                await bot.edit_message_text(f"❌ Login failed. Response: {r.text}", chat_id=message.chat.id, message_id=status_msg.message_id)
                auth_sessions.pop(user_id, None)
                return

            await bot.edit_message_text("✅ Login successful! Extracting API data...", chat_id=message.chat.id, message_id=status_msg.message_id)

            r_apps = await asyncio.to_thread(s.get, 'https://my.telegram.org/apps', timeout=15)
            soup = BeautifulSoup(r_apps.text, 'html.parser')
            info = extract_app_info(soup)

            api_id = info.get('api_id')
            api_hash = info.get('api_hash')

            if not api_id or not api_hash:
                await bot.edit_message_text("🆕 No API keys found. Creating a new Application...", chat_id=message.chat.id, message_id=status_msg.message_id)

                name = "app_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
                create_hash = None
                hash_input = soup.find("input", {"name": "hash"})
                if hash_input:
                    create_hash = hash_input.get("value")

                create_payload = {
                    "hash": create_hash,
                    "app_title": name,
                    "app_shortname": name,
                    "app_url": "https://example.com",
                    "app_platform": "android",
                    "app_desc": ""
                }
                await asyncio.to_thread(s.post, "https://my.telegram.org/apps/create", data=create_payload, timeout=15)
                r_apps = await asyncio.to_thread(s.get, "https://my.telegram.org/apps", timeout=15)
                soup = BeautifulSoup(r_apps.text, "html.parser")
                info = extract_app_info(soup)
                api_id = info.get('api_id')
                api_hash = info.get('api_hash')

            if api_id and api_hash:
                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                result_parts = [
                    "✨ <b>Telegram API Info Fetched!</b>\n",
                    f"🔹 <b>API ID:</b> <code>{api_id}</code>",
                    f"🔹 <b>API HASH:</b> <code>{api_hash}</code>"
                ]
                if info.get('app_title'):
                    result_parts.append(f"🔹 <b>App Title:</b> <code>{info.get('app_title')}</code>")
                if info.get('short_name'):
                    result_parts.append(f"🔹 <b>Short Name:</b> <code>{info.get('short_name')}</code>")
                if info.get('production_config'):
                    result_parts.append(f"\n⚙️ <b>Production Config:</b>\n<code>{info.get('production_config')}</code>")
                if info.get('prod_public_key'):
                    result_parts.append(f"\n🔑 <b>Public Keys:</b>\n<code>{info.get('prod_public_key')}</code>")

                result_parts.append("\n⚠️ <b>Keep these safe!</b> Do not share these keys with anyone.")
                result_parts.append(f"\n{footer}")

                full_message = "\n".join(result_parts)
                if len(full_message) > 4096:
                    await bot.send_message(message.chat.id, full_message[:4096], parse_mode="HTML")
                    await bot.send_message(message.chat.id, full_message[4096:], parse_mode="HTML")
                else:
                    await bot.send_message(message.chat.id, full_message, parse_mode="HTML")

                await bot.delete_message(message.chat.id, status_msg.message_id)
            else:
                await bot.edit_message_text("❌ Failed to extract API keys. You might need to create them manually at my.telegram.org.", chat_id=message.chat.id, message_id=status_msg.message_id)

        except Exception as e:
            await bot.edit_message_text(f"❌ Error during processing: {str(e)}", chat_id=message.chat.id, message_id=status_msg.message_id)
        finally:
            auth_sessions.pop(user_id, None)


def extract_app_info(soup):
    info = {}

    def get_first_labeled_value(label_texts):
        for label in soup.find_all('label'):
            text = label.get_text(strip=True).lower()
            if any(lt in text for lt in label_texts):
                div = label.find_next_sibling('div')
                if div:
                    inp = div.find('input')
                    if inp and inp.get('value'):
                        return inp.get('value')
                    for tag in div.find_all(['span', 'textarea', 'pre', 'code', 'strong']):
                        val = tag.get_text(strip=True)
                        if val:
                            return val
        return None

    info['api_id'] = get_first_labeled_value(['api_id', 'api id'])
    info['api_hash'] = get_first_labeled_value(['api_hash', 'api hash'])
    info['app_title'] = get_first_labeled_value(['app title', 'title'])
    info['short_name'] = get_first_labeled_value(['short name'])

    public_keys = []
    for label in soup.find_all('label'):
        if 'public keys' in label.get_text(strip=True).lower():
            div = label.find_next_sibling('div')
            if div:
                pre = div.find('pre')
                if pre:
                    public_keys.append(pre.get_text(strip=True))
                else:
                    code = div.find('code')
                    if code:
                        public_keys.append(code.get_text(strip=True))
    if public_keys:
        info['public_keys'] = public_keys

    info['test_config'] = get_first_labeled_value(['test configuration'])
    info['production_config'] = get_first_labeled_value(['production configuration'])

    def get_key_from_section(section_label_text):
        for label in soup.find_all('label'):
            if section_label_text in label.get_text(strip=True).lower():
                parent_div = label.find_parent('div', class_='form-group')
                if not parent_div:
                    continue
                for sibling in parent_div.find_next_siblings('div', class_='form-group'):
                    sibling_label = sibling.find('label')
                    if sibling_label:
                        lbl_text = sibling_label.get_text(strip=True).lower()
                        if 'public keys' in lbl_text:
                            pre = sibling.find('pre')
                            if pre:
                                return pre.get_text(strip=True)
                            code = sibling.find('code')
                            if code:
                                return code.get_text(strip=True)
                        if 'configuration' in lbl_text:
                            break
        return None

    info['test_public_key'] = get_key_from_section('test configuration')
    info['prod_public_key'] = get_key_from_section('production configuration')
    return info
