import requests
import html
import time
import random
import string
import hashlib
from telebot import types
import asyncio

# --- Constants & Configuration ---
TEMP_TOOL_API = "https://temp.bbinl.eu.cc"
MAIL_CACHE = {}
REQUESTER_CACHE = {} 

DOMAIN_LISTS = {
    "tmailor": [
        "bltiwd.com", "daouse.com", "illubd.com", "mkzaso.com", "mrotzis.com", 
        "xkxkud.com", "wnbaldwy.com", "bwmyga.com", "ozsaip.com", "yzcalo.com", 
        "lnovic.com", "ruutukf.com"
    ],
    "tempmailio": [
        "bltiwd.com", "daouse.com", "illubd.com", "mkzaso.com", "mrotzis.com", 
        "xkxkud.com", "wnbaldwy.com", "bwmyga.com", "ozsaip.com", "yzcalo.com", 
        "lnovic.com", "ruutukf.com"
    ],
    "edumailfree": [
        "academic.edu.rs", "semar.edu.pl", "gng.edu.pl", "agp.edu.pl", "gold.edu.pl", 
        "bcm.edu.pl", "id.semar.edu.pl", "dev.semar.edu.pl", "student.semar.edu.pl", 
        "teacher.semar.edu.pl", "portal.academic.edu.rs", "contact.academic.edu.rs", 
        "students.academic.edu.rs", "library.gng.edu.pl", "research.gng.edu.pl", 
        "exams.gng.edu.pl", "lab.agp.edu.pl", "up.agp.edu.pl", "campus.agp.edu.pl", 
        "prime.gold.edu.pl", "student.gold.edu.pl", "elite.gold.edu.pl", "dev.bcm.edu.pl", 
        "webmail.bcm.edu.pl", "hr.bcm.edu.pl", "student.neonet.ac.nz"
    ]
}

# --- API Functions ---
async def tmailor_gen(username=None, domain=None):
    params = {}
    if username: params['username'] = username
    if domain: params['domain'] = domain
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tmailor/gen", params=params, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def tmailor_inbox(key, email):
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tmailor/inbox", params={"key": key, "email": email}, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def tempmailio_gen(username=None, domain=None):
    params = {}
    if username: params['username'] = username
    if domain: params['domain'] = domain
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tempmailio/gen", params=params, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def tempmailio_inbox(key, email):
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tempmailio/inbox", params={"key": key, "email": email}, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def tempmailorg_gen():
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tempmailorg/gen", timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def tempmailorg_inbox(key, email=None):
    params = {"key": key}
    if email: params['email'] = email
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tempmailorg/inbox", params=params, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def edumailfree_gen(username=None, domain=None):
    params = {}
    if username: params['username'] = username
    if domain: params['domain'] = domain
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/edumailfree/gen", params=params, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def edumailfree_inbox(key):
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/edumailfree/inbox", params={"key": key}, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def etempmail_gen():
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/etempmail/gen", timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

async def etempmail_inbox(key, email=None):
    params = {"key": key}
    if email: params['email'] = email
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/etempmail/inbox", params=params, timeout=15)
        return res.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- Helper functions ---
def generate_random_username():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(6, 10)))

def get_cache_id(data):
    cache_id = hashlib.md5(str(data).encode()).hexdigest()[:10]
    MAIL_CACHE[cache_id] = data
    if len(MAIL_CACHE) > 1000:
        keys = list(MAIL_CACHE.keys())
        for k in keys[:200]:
            MAIL_CACHE.pop(k, None)
    return cache_id

def create_service_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("TMailor", callback_data="tm_srv:tmailor"),
        types.InlineKeyboardButton("TempMail.io", callback_data="tm_srv:tempmailio"),
        types.InlineKeyboardButton("ETempMail", callback_data="tm_srv:etempmail"),
        types.InlineKeyboardButton("EduMailFree", callback_data="tm_srv:edumailfree"),
        types.InlineKeyboardButton("TempMail.org", callback_data="tm_srv:tempmailorg")
    )
    return markup

def create_domain_keyboard(service):
    domains = DOMAIN_LISTS.get(service, [])
    markup = types.InlineKeyboardMarkup(row_width=2)
    for dom in domains:
        markup.add(types.InlineKeyboardButton(dom, callback_data=f"tm_dom:{service}:{dom}"))
    return markup

def create_user_selection_keyboard(service, domain):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Random Selection", callback_data=f"tm_usr:{service}:{domain}:rnd"),
        types.InlineKeyboardButton("Custom Username", callback_data=f"tm_usr:{service}:{domain}:cus")
    )
    return markup

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    
    @custom_command_handler("tmail")
    async def handle_tmail(message):
        if check_usage_limit and not await check_usage_limit(message, "Temp Mail"):
            return
        
        sent = await bot.reply_to(
            message,
            "📩 <b>Temp Mail System</b>\nSelect a mail service from the options below:",
            reply_markup=create_service_keyboard(),
            parse_mode="HTML"
        )
        REQUESTER_CACHE[(sent.chat.id, sent.message_id)] = message.from_user.id
        
        # Cleanup REQUESTER_CACHE periodically
        if len(REQUESTER_CACHE) > 500:
            keys = list(REQUESTER_CACHE.keys())
            for k in keys[:100]:
                REQUESTER_CACHE.pop(k, None)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("tm_"))
    async def tm_callback_handler(call):
        parts = call.data.split(":")
        action = parts[0]
        
        user = call.from_user
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        
        # Requester Validation
        requester_id = REQUESTER_CACHE.get((chat_id, msg_id))
        
        # Check MAIL_CACHE if not in REQUESTER_CACHE (for deeper navigation)
        if not requester_id and action in ["tm_inb", "tm_msg"]:
            cache_id = parts[1]
            cache_data = MAIL_CACHE.get(cache_id)
            if cache_data:
                requester_id = cache_data.get('requester_id')

        if requester_id and user.id != requester_id:
            await bot.answer_callback_query(call.id, "❌ This is not your request! Only the original requester can use these buttons.", show_alert=True)
            return

        username_str = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username_str}"

        if action == "tm_srv":
            service = parts[1]
            if service in ["tmailor", "tempmailio", "edumailfree"]:
                await bot.edit_message_text(f"🌐 <b>Select Domain for {service.capitalize()}:</b>", 
                                    call.message.chat.id, call.message.message_id, 
                                    reply_markup=create_domain_keyboard(service),
                                    parse_mode="HTML")
            else:
                await generate_and_send(call, service, None, None)
            
            # Transfer requester info on edit
            if requester_id:
                REQUESTER_CACHE[(call.message.chat.id, call.message.message_id)] = requester_id

        elif action == "tm_dom":
            service = parts[1]
            domain = parts[2]
            await bot.edit_message_text(f"👤 <b>Service:</b> {service}\n🌐 <b>Domain:</b> {domain}\n\nChoose username generation type:",
                                call.message.chat.id, call.message.message_id,
                                reply_markup=create_user_selection_keyboard(service, domain),
                                parse_mode="HTML")

        elif action == "tm_usr":
            service = parts[1]
            domain = parts[2]
            u_type = parts[3]
            
            if u_type == "rnd":
                await generate_and_send(call, service, domain, generate_random_username())
            else:
                sent = await bot.edit_message_text("✍️ <b>Please reply with your desired username:</b>", 
                                            call.message.chat.id, call.message.message_id, 
                                            parse_mode="HTML")
                await bot.register_next_step_handler(call.message, handle_custom_username, service, domain, sent.message_id)

        elif action == "tm_inb":
            cache_id = parts[1]
            cache_data = MAIL_CACHE.get(cache_id)
            if not cache_data:
                await bot.answer_callback_query(call.id, "❌ Session expired.")
                return
            
            service = cache_data['service']
            key = cache_data['key']
            email = cache_data.get('email')
            await bot.answer_callback_query(call.id, "🔄 Checking inbox...")
            
            if service == "tmailor": data = await tmailor_inbox(key, email)
            elif service == "tempmailio": data = await tempmailio_inbox(key, email)
            elif service == "tempmailorg": data = await tempmailorg_inbox(key, email)
            elif service == "edumailfree": data = await edumailfree_inbox(key)
            elif service == "etempmail": data = await etempmail_inbox(key, email)
            else: data = {"success": False}
            
            if data.get("success"):
                messages = data.get("data", {}).get("messages", [])
                if not messages:
                    await bot.answer_callback_query(call.id, "📭 Inbox is empty!")
                    return
                
                cache_data['messages'] = messages
                MAIL_CACHE[cache_id] = cache_data
                text = f"📬 <b>{service.capitalize()} Inbox ({len(messages)} messages):</b>\n\n"
                markup = types.InlineKeyboardMarkup(row_width=5)
                msg_btns = []
                for idx, msg in enumerate(messages, 1):
                    sender = msg.get('from') or msg.get('sender') or 'Unknown'
                    subject = msg.get('subject') or 'No Subject'
                    text += f"<b>{idx}. From:</b> {html.escape(str(sender))}\n"
                    text += f"<b>Subject:</b> {html.escape(str(subject))}\n\n"
                    msg_btns.append(types.InlineKeyboardButton(str(idx), callback_data=f"tm_msg:{cache_id}:{idx-1}"))
                
                deep_link = f"{TEMP_TOOL_API}/tmail?service={service}&email={email}&key={key}"
                
                markup.add(*msg_btns)
                markup.add(types.InlineKeyboardButton("🔄 Refresh", callback_data=f"tm_inb:{cache_id}"),
                           types.InlineKeyboardButton("🌐 Web Inbox", url=deep_link))
                
                await bot.edit_message_text(text + footer, call.message.chat.id, call.message.message_id, 
                                    reply_markup=markup, parse_mode="HTML")
            else:
                await bot.answer_callback_query(call.id, "❌ Failed to fetch inbox.")

        elif action == "tm_msg":
            cache_id = parts[1]
            msg_idx = int(parts[2])
            cache_data = MAIL_CACHE.get(cache_id)
            if not cache_data or 'messages' not in cache_data:
                await bot.answer_callback_query(call.id, "❌ Message data not found.")
                return
            
            msg = cache_data['messages'][msg_idx]
            sender = msg.get('from') or msg.get('sender') or 'Unknown'
            subject = msg.get('subject') or 'No Subject'
            body = msg.get('body_text')
            
            if not body:
                raw_body = msg.get('body') or 'No content'
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(raw_body, 'html.parser')
                    body = soup.get_text(separator='\n', strip=True)
                except Exception:
                    body = raw_body
            
            if len(body) > 3500:
                body = body[:3500] + "\n\n[Content Truncated]"

            import re
            links = re.findall(r'(https?://\S+)', body)
            open_link_btn = None
            if links:
                open_link_btn = types.InlineKeyboardButton(" Open Link", url=links[0])

            safe_body = html.escape(str(body))
            safe_body = re.sub(r'(?<!\d)(\d{4,8})(?!\d)', r'<code>\1</code>', safe_body)
            
            if len(safe_body) > 3500:
                safe_body = safe_body[:3500] + "\n\n[Content Truncated]"

            text = f"📧 <b>Message Details (#{msg_idx+1})</b>\n\n"
            text += f"👤 <b>From:</b> {html.escape(str(sender))}\n"
            text += f"🎯 <b>Subject:</b> {html.escape(str(subject))}\n"
            text += f"📝 <b>Body:</b>\n{safe_body}"
            
            markup = types.InlineKeyboardMarkup()
            row_btns = [types.InlineKeyboardButton("⬅️ Back to Inbox", callback_data=f"tm_inb:{cache_id}")]
            if open_link_btn:
                row_btns.append(open_link_btn)
            
            markup.add(*row_btns)
            
            await bot.edit_message_text(text + footer, call.message.chat.id, call.message.message_id, 
                                reply_markup=markup, parse_mode="HTML")

    async def handle_custom_username(message, service, domain, edit_msg_id):
        username = message.text.strip().split()[0]
        try: await bot.delete_message(message.chat.id, message.message_id)
        except: pass
        
        class FakeCall:
            def __init__(self, message, from_user):
                self.message = message
                self.from_user = from_user
                self.id = "0"
            async def answer_callback_query(self, *args, **kwargs): pass
        
        await generate_and_send(FakeCall(message, message.from_user), service, domain, username, edit_msg_id)

    async def generate_and_send(call, service, domain, username, edit_msg_id=None):
        chat_id = call.message.chat.id
        msg_id = edit_msg_id or call.message.message_id
        await bot.edit_message_text("🔄 Generating email...", chat_id, msg_id)
        
        data = {"success": False}
        if service == "tmailor": data = await tmailor_gen(username, domain)
        elif service == "tempmailio": data = await tempmailio_gen(username, domain)
        elif service == "tempmailorg": data = await tempmailorg_gen()
        elif service == "edumailfree": data = await edumailfree_gen(username, domain)
        elif service == "etempmail": data = await etempmail_gen()
        
        user = call.from_user
        username_str = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘁 𝗯𝘆: {username_str}"

        if data.get("success"):
            email = data["data"].get("email")
            key = data["data"].get("key") or data["data"].get("token")
            
            cache_id = get_cache_id({"service": service, "key": key, "email": email, "requester_id": call.from_user.id})
            deep_link = f"{TEMP_TOOL_API}/tmail?service={service}&email={email}&key={key}"
            res_text = f"✨ <b>{service.capitalize()} Generated!</b>\n\n"
            res_text += f"📧 <b>Email:</b> <code>{email}</code>\n"
            res_text += f"🔑 <b>Key:</b> <code>{key}</code>\n\n"
            res_text += f"💡 Click the buttons below to check inbox."
            
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("📬 Check Inbox (Bot)", callback_data=f"tm_inb:{cache_id}"))
            markup.row(types.InlineKeyboardButton("🌐 Open Inbox (Web)", url=deep_link))
            
            await bot.edit_message_text(res_text + footer, chat_id, msg_id, reply_markup=markup, parse_mode="HTML")
        else:
            await bot.edit_message_text(f"❌ Generation failed: {data.get('message', 'Unknown error')}" + footer, 
                                chat_id, msg_id, parse_mode="HTML")
