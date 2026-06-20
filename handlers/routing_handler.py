import html
import requests

ROUTING_API_URL = "https://routing.bbinl.eu.cc/api/gen"

async def generate_routing_data(limit=5):
    """Generate routing numbers using the API"""
    try:
        response = await asyncio.to_thread(requests.get, ROUTING_API_URL, timeout=10)
        data = response.json()
        
        if not data:
            return "❌ No routing data received from API"

        results = []
        
        for item in data[:limit]:
            routing_number = item.get("routing_number", "N/A")
            account_number = item.get("account_number", "N/A")
            bank_name = item.get("bank_name", "N/A")
            city = item.get("city", "N/A")
            state = item.get("state", "N/A")
            zip_code = item.get("zip", "N/A")
            
            address_parts = []
            if city:
                address_parts.append(city)
            if state:
                address_parts.append(state)
            if zip_code:
                address_parts.append(zip_code)
            
            address = ", ".join(address_parts) if address_parts else "N/A"
            
            output = (
                f"<b>𝗥𝗼𝘂𝘁𝗶𝗻𝗴:</b> <code>{html.escape(routing_number)}</code>\n"
                f"<b>𝗔𝗰𝗰𝗼𝘂𝗻𝘁:</b> <code>{html.escape(account_number)}</code>\n"
                f"•━━━━━ 𝗥𝗼𝘂𝘁𝗶𝗻𝗴 𝗜𝗻𝗳𝗼 ━━━━━•\n"
                f"<b>𝗕𝗮𝗻𝗸:</b> <code>{html.escape(bank_name)}</code>\n"
                f"<b>𝗔𝗱𝗱𝗿𝗲𝘀𝘀:</b> <code>{html.escape(address)}</code>\n"
                f"•━━━━━━━━━━━━━━━━━━•"
            )
            
            results.append(output)

        return "\n\n".join(results)

    except Exception as e:
        return f"⚠️ Error generating routing data: {str(e)}"

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

def get_regen_markup(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("♻️ Regenerate", callback_data=f"regen_routing:{user_id}"))
    return markup

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("regen_routing:"))
    async def callback_regen_routing(call):
        parts = call.data.split(":")
        original_user_id = parts[1]
        
        if str(call.from_user.id) != str(original_user_id):
            await bot.answer_callback_query(call.id, "❌ Only the original requester can regenerate this.", show_alert=True)
            return

        try:
            await bot.answer_callback_query(call.id, "♻️ Generating new routing numbers...")
            result = await generate_routing_data(limit=5)
            
            username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            markup = get_regen_markup(original_user_id)
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{result}\n{footer}",
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            await bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)

    @custom_command_handler("rut")
    @custom_command_handler("routing")
    async def handle_route(message):
        if check_usage_limit and not await check_usage_limit(message, "Routing"):
            return
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

        sent_msg = await bot.reply_to(message, "🔄 Generating routing numbers...", parse_mode="HTML")
        
        result = await generate_routing_data(limit=5)
        
        try:
            markup = get_regen_markup(message.from_user.id)
            await bot.edit_message_text(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                text=f"{result}\n{footer}",
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            await bot.reply_to(message, f"⚠️ Failed to edit message: {str(e)}")
