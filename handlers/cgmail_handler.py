import requests
import html
from telebot import types
import re
import os
import asyncio

API_URL = "https://xmail-checker.vercel.app/api/check"

async def check_emails(email_list):
    try:
        payload = {"mail": email_list, "fastCheck": False}
        response = await asyncio.to_thread(requests.post, API_URL, json=payload, timeout=20)
        
        if response.status_code != 200:
            return None, f"API Error: {response.status_code}"
            
        return response.json(), None
    except Exception as e:
        return None, str(e)

def format_status(status):
    s_lower = status.lower()
    
    if any(x in s_lower for x in ["live", "valid"]):
        return "🟢", status
    elif any(x in s_lower for x in ["disabled", "unregistered", "does not exist", "invalid"]):
        return "🔴", status
    else:
        return "🟡", status

def extract_emails(text):
    if not text:
        return []
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    
    @custom_command_handler("cgmail")
    async def handle_cgmail(message):
        if check_usage_limit and not await check_usage_limit(message, "Mail Check"):
            return

        # 1. Get emails from message or reply
        emails_to_check = []
        
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            emails_to_check.extend(extract_emails(parts[1]))
            
        if message.reply_to_message and message.reply_to_message.text:
            emails_to_check.extend(extract_emails(message.reply_to_message.text))
            
        seen = set()
        unique_emails = [x for x in emails_to_check if not (x in seen or seen.add(x))]
        
        if not unique_emails:
            await bot.reply_to(message, "❌ No emails found. Please provide emails after the command or reply to a message containing emails.")
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

        sent_msg = await bot.reply_to(message, f"🔄 Checking {len(unique_emails)} emails...", parse_mode="HTML")

        # 2. Call API
        data, error = await check_emails(unique_emails)
        
        if error:
            await bot.edit_message_text(f"❌ Error checking emails: {html.escape(error)}", sent_msg.chat.id, sent_msg.message_id)
            return

        if not data or "results" not in data:
            await bot.edit_message_text("❌ No results returned from API.", sent_msg.chat.id, sent_msg.message_id)
            return

        results = data.get("results", [])
        
        # 3. Format output
        output_lines = []
        for res in results:
            email = res.get("email", "Unknown")
            status = res.get("status", "Unknown")
            emoji, fmt_status = format_status(status)
            output_lines.append(f"{emoji} <b>Email:</b> <code>{email}</code>\n<b>Status:</b> {fmt_status}")

        formatted_output = "\n\n".join(output_lines)
        full_message = f"📧 <b>Mail Check Results</b>\n\n{formatted_output}{footer}"

        # 4. Handle long messages
        if len(full_message) > 4000:
            filename = f"mail_check_{message.id}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                for res in results:
                    email = res.get("email", "Unknown")
                    status = res.get("status", "Unknown")
                    f.write(f"Email: {email} | Status: {status}\n")
            
            try:
                with open(filename, "rb") as f:
                    await bot.send_document(
                        message.chat.id, 
                        f, 
                        caption=f"📧 <b>Mail Check Results</b>\n\n✅ Checked {len(results)} emails.\n📄 File attached due to length.{footer}",
                        parse_mode="HTML",
                        reply_to_message_id=message.message_id
                    )
                await bot.delete_message(sent_msg.chat.id, sent_msg.message_id) # Delete "Checking..." message
            except Exception as e:
                await bot.edit_message_text(f"❌ Error sending file: {e}", sent_msg.chat.id, sent_msg.message_id)
            finally:
                if os.path.exists(filename):
                    os.remove(filename)
        else:
            try:
                await bot.edit_message_text(full_message, sent_msg.chat.id, sent_msg.message_id, parse_mode="HTML")
            except Exception as e:
                await bot.reply_to(message, f"❌ Error sending results: {e}")
