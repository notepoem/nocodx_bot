import requests
import html
import hashlib
from telebot import types
import asyncio

# --- Constants & Configuration ---
TEMP_TOOL_API = "https://temp.bbinl.eu.cc"
NUM_CACHE = {}
REQUESTER_CACHE_NUM = {} 

# --- API Functions ---
async def get_countries_list():
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tnumber/api/list", timeout=15)
        return res.json()
    except Exception as e:
        return []

async def get_numbers_list(country_slug, page=1):
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tnumber/api/{country_slug}", params={"page": page}, timeout=15)
        return res.json()
    except Exception as e:
        return {"numbers": [], "current_page": 1, "max_page": 1}

async def get_number_otps(country_slug, number, page=1):
    try:
        res = await asyncio.to_thread(requests.get, f"{TEMP_TOOL_API}/tnumber/api/{country_slug}/otp", params={"num": number, "page": page}, timeout=15)
        return res.json()
    except Exception as e:
        return {"messages": [], "current_page": 1, "max_page": 1}

# --- Helper functions ---
def get_num_cache_id(data):
    cache_id = hashlib.md5(str(data).encode()).hexdigest()[:10]
    NUM_CACHE[cache_id] = data
    if len(NUM_CACHE) > 1000:
        keys = list(NUM_CACHE.keys())
        for k in keys[:200]:
            NUM_CACHE.pop(k, None)
    return cache_id

async def create_country_keyboard(page=1):
    countries = await get_countries_list()
    page_size = 14
    total_pages = (len(countries) + page_size - 1) // page_size
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_countries = countries[start_idx:end_idx]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for c in page_countries:
        btns.append(types.InlineKeyboardButton(c['name'], callback_data=f"tn_cou:{c['slug']}"))
    markup.add(*btns)
    
    # Pagination
    nav_btns = []
    if page > 1:
        nav_btns.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"tn_cpn:{page-1}"))
    if page < total_pages:
        nav_btns.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"tn_cpn:{page+1}"))
    if nav_btns:
        markup.row(*nav_btns)
        
    return markup

async def create_numbers_keyboard(country_slug, page=1):
    data = await get_numbers_list(country_slug, page)
    numbers = data.get('numbers', [])
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for n in numbers:
        # number is usually like "1234567890"
        btns.append(types.InlineKeyboardButton(f"📞 {n['number']}", callback_data=f"tn_sel:{country_slug}:{n['number']}"))
    markup.add(*btns)
    
    # Pagination
    nav_btns = []
    if page > 1:
        nav_btns.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"tn_pgn:{country_slug}:{page-1}"))
    if page < data.get('max_page', 1):
        nav_btns.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"tn_pgn:{country_slug}:{page+1}"))
    if nav_btns:
        markup.row(*nav_btns)
        
    return markup

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None, **kwargs):
    
    @custom_command_handler("tnumber")
    async def handle_tnumber(message):
        if check_usage_limit and not await check_usage_limit(message, "Temp Number"):
            return
        
        sent = await bot.reply_to(
            message,
            "📞 <b>Temp Number System</b>\nSelect a country to view available numbers:",
            reply_markup=await create_country_keyboard(page=1),
            parse_mode="HTML"
        )
        REQUESTER_CACHE_NUM[(sent.chat.id, sent.message_id)] = message.from_user.id

    @bot.callback_query_handler(func=lambda call: call.data.startswith("tn_"))
    async def tn_callback_handler(call):
        parts = call.data.split(":")
        action = parts[0]
        
        user = call.from_user
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        
        # Requester Validation
        requester_id = REQUESTER_CACHE_NUM.get((chat_id, msg_id))
        if requester_id and user.id != requester_id:
            await bot.answer_callback_query(call.id, "❌ This is not your request!", show_alert=True)
            return

        username_str = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username_str}"

        if action == "tn_cpn":
            page = int(parts[1])
            await bot.edit_message_text("📞 <b>Temp Number System</b>\nSelect a country to view available numbers:",
                                chat_id, msg_id,
                                reply_markup=await create_country_keyboard(page),
                                parse_mode="HTML")

        elif action == "tn_cou":
            country_slug = parts[1]
            await bot.edit_message_text(f"🌐 <b>Country:</b> {country_slug.replace('-', ' ').title()}\nSelect a number:",
                                chat_id, msg_id,
                                reply_markup=await create_numbers_keyboard(country_slug),
                                parse_mode="HTML")

        elif action == "tn_pgn":
            country_slug = parts[1]
            page = int(parts[2])
            await bot.edit_message_text(f"🌐 <b>Country:</b> {country_slug.replace('-', ' ').title()}\nSelect a number (Page {page}):",
                                chat_id, msg_id,
                                reply_markup=await create_numbers_keyboard(country_slug, page),
                                parse_mode="HTML")

        elif action == "tn_sel":
            country_slug = parts[1]
            number = parts[2]
            
            res_text = f"📞 <b>Number Selected!</b>\n\n"
            res_text += f"📱 <b>Number:</b> <code>+{number}</code>\n"
            res_text += f"🌐 <b>Country:</b> {country_slug.replace('-', ' ').title()}\n\n"
            res_text += f"💡 Click below to check for incoming OTPs."
            
            markup = types.InlineKeyboardMarkup()
            cache_id = get_num_cache_id({"slug": country_slug, "num": number, "requester_id": user.id})
            web_url = f"{TEMP_TOOL_API}/tnumber/number/{country_slug}/{number}"
            
            markup.add(types.InlineKeyboardButton("📨 Check OTPs", callback_data=f"tn_otp:{cache_id}:1"))
            markup.add(types.InlineKeyboardButton("🌐 Open In Web", url=web_url))
            markup.add(types.InlineKeyboardButton("⬅️ Back to List", callback_data=f"tn_cou:{country_slug}"))
            
            await bot.edit_message_text(res_text + footer, chat_id, msg_id, reply_markup=markup, parse_mode="HTML")

        elif action == "tn_otp":
            cache_id = parts[1]
            page = int(parts[2])
            cache_data = NUM_CACHE.get(cache_id)
            if not cache_data:
                await bot.answer_callback_query(call.id, "❌ Session expired.")
                return
            
            await bot.answer_callback_query(call.id, "🔄 Fetching messages...")
            
            data = await get_number_otps(cache_data['slug'], cache_data['num'], page)
            messages = data.get('messages', [])
            
            if not messages:
                await bot.answer_callback_query(call.id, "📭 No messages found yet!", show_alert=True)
                return
            
            text = f"📬 <b>Messages for +{cache_data['num']}:</b>\n\n"
            for msg in messages:
                text += f"👤 <b>From:</b> {html.escape(msg.get('sender', 'Unknown'))}\n"
                text += f"⌚ <b>Time:</b> {msg.get('time', '')}\n"
                text += f"💬 <code>{html.escape(msg.get('body', ''))}</code>\n"
                if msg.get('otp'):
                    text += f"🔑 <b>OTP:</b> <code>{msg['otp']}</code>\n"
                text += "─────────────────\n"
            
            markup = types.InlineKeyboardMarkup()
            nav_btns = []
            if page > 1:
                nav_btns.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"tn_otp:{cache_id}:{page-1}"))
            
            nav_btns.append(types.InlineKeyboardButton("🔄 Refresh", callback_data=f"tn_otp:{cache_id}:{page}"))
            
            if page < data.get('max_page', 1):
                nav_btns.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"tn_otp:{cache_id}:{page+1}"))
            
            markup.row(*nav_btns)
            markup.add(types.InlineKeyboardButton("⬅️ Back to Number", callback_data=f"tn_sel:{cache_data['slug']}:{cache_data['num']}"))
            await bot.edit_message_text(text + footer, chat_id, msg_id, reply_markup=markup, parse_mode="HTML")
