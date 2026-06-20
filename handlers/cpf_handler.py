import requests
import html

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

def get_regen_markup(amount, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("♻️ Regenerate", callback_data=f"regen_cpf:{amount}:{user_id}"))
    return markup

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit):
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("regen_cpf:"))
    async def callback_regen_cpf(call):
        parts = call.data.split(":")
        amount = int(parts[1])
        original_user_id = parts[2]
        
        if str(call.from_user.id) != str(original_user_id):
            await bot.answer_callback_query(call.id, "❌ Only the original requester can regenerate this.", show_alert=True)
            return

        try:
            await bot.answer_callback_query(call.id, "♻️ Generating new CPF...")
            api_url = f"https://cpf-blond.vercel.app/api/cpf?amount={amount}"
            response = await asyncio.to_thread(requests.get, api_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data or not isinstance(data, list):
                await bot.answer_callback_query(call.id, "❌ Failed to generate CPF data.", show_alert=True)
                return
                
            username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            response_text = f"✅ <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 {len(data)} 𝗖𝗣𝗙:</b>\n\n"
            for item in data:
                name = item.get("Name", "N/A")
                cpf = item.get("CPF", "N/A")
                dob = item.get("DATE_of_BIRTH", "N/A")
                center = item.get("CENTER", "N/A")
                
                response_text += f"👤 <b>𝗡𝗮𝗺𝗲:</b> <code>{html.escape(name)}</code>\n"
                response_text += f"💳 <b>𝗖𝗣𝗙:</b> <code>{html.escape(cpf)}</code>\n"
                response_text += f"📅 <b>𝗗𝗢𝗕:</b> <code>{html.escape(dob)}</code>\n"
                response_text += f"📍 <b>𝗖𝗲𝗻𝘁𝗲𝗿:</b> <code>{html.escape(center)}</code>\n"
                response_text += "•─────────────────•\n"
            
            response_text += footer
            
            markup = get_regen_markup(amount, original_user_id)
            await bot.edit_message_text(response_text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
            
        except Exception as e:
            await bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)

    @custom_command_handler("cpf")
    async def handle_cpf(message):
        if not await check_usage_limit(message, "CPF"):
            return
            
        parts = message.text.split()
        amount = 1
        if len(parts) > 1:
            try:
                amount = int(parts[1])
                if amount > 20: amount = 20
                if amount < 1: amount = 1
            except ValueError:
                amount = 1
                
        sent_msg = await bot.reply_to(message, f"🔍 Generating {amount} CPF...")
        
        try:
            api_url = f"https://cpf-sage.vercel.app/api/cpf?amount={amount}"
            response = await asyncio.to_thread(requests.get, api_url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data or not isinstance(data, list):
                await bot.edit_message_text("❌ Failed to generate CPF data.", message.chat.id, sent_msg.message_id)
                return
                
            username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            response_text = f"✅ <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 {len(data)} 𝗖𝗣𝗙:</b>\n\n"
            for item in data:
                name = item.get("Name", "N/A")
                cpf = item.get("CPF", "N/A")
                dob = item.get("DATE_of_BIRTH", "N/A")
                center = item.get("CENTER", "N/A")
                
                response_text += f"👤 <b>𝗡𝗮𝗺𝗲:</b> <code>{html.escape(name)}</code>\n"
                response_text += f"💳 <b>𝗖𝗣𝗙:</b> <code>{html.escape(cpf)}</code>\n"
                response_text += f"📅 <b>𝗗𝗢𝗕:</b> <code>{html.escape(dob)}</code>\n"
                response_text += f"📍 <b>𝗖𝗲𝗻𝘁𝗲𝗿:</b> <code>{html.escape(center)}</code>\n"
                response_text += "•─────────────────•\n"
            
            response_text += footer
            
            markup = get_regen_markup(amount, message.from_user.id)
            await bot.edit_message_text(response_text, message.chat.id, sent_msg.message_id, parse_mode="HTML", reply_markup=markup)
            
        except Exception as e:
            await bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, sent_msg.message_id)
