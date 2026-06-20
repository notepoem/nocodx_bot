import requests
import html
from telebot import types
import re
import os
import asyncio
import uuid
import json
import websocket
import threading

API_CHECK_URL = "https://check-gmail.live/api/check"
WS_URL = "wss://check-gmail.live/ws"

def check_emails_sync(email_list):
    results = {}
    total_emails = len(email_list)
    completed = threading.Event()
    my_session_id = None
    
    ws_headers = {
        "Origin": "https://check-gmail.live",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }
    
    def on_message(ws, message):
        try:
            msg = json.loads(message)
            msg_type = msg.get("type")
            
            if msg_type == "session":
                nonlocal my_session_id
                my_session_id = msg.get("sessionId")
                
                # Trigger HTTP POST request
                threading.Thread(target=trigger_post, args=(ws,)).start()
                
            elif msg_type == "batch":
                batch_results = msg.get("results", [])
                for res in batch_results:
                    email = res.get("email")
                    status = res.get("status")
                    if email and status:
                        results[email] = status.capitalize()
                
                if len(results) >= total_emails:
                    completed.set()
                    
            elif msg_type == "done":
                completed.set()
                
            elif msg_type == "error":
                completed.set()
                
        except Exception:
            pass
            
    def trigger_post(ws):
        headers = {
            'Accept': '*/*',
            'Content-Type': 'application/json',
            'Origin': 'https://check-gmail.live',
            'Referer': 'https://check-gmail.live/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
        }
        json_data = {
            'emails': email_list,
            'fastCheck': False,
            'checkFlag': False,
            'sessionId': my_session_id,
        }
        
        try:
            response = requests.post(API_CHECK_URL, headers=headers, json=json_data, timeout=15)
            if response.status_code != 200:
                completed.set()
        except Exception:
            completed.set()
            
    def on_open(ws):
        pass
            
    def on_error(ws, error):
        completed.set()
        
    def on_close(ws, close_status_code, close_msg):
        completed.set()
            
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=on_message,
        on_open=on_open,
        on_error=on_error,
        on_close=on_close,
        header=[f"{k}: {v}" for k, v in ws_headers.items()]
    )
    
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    completed.wait(timeout=35)
    ws.close()
    
    results_list = [{"email": k, "status": v} for k, v in results.items()]
    return {"results": results_list}

async def check_emails(email_list):
    try:
        data = await asyncio.to_thread(check_emails_sync, email_list)
        if not data or not data.get("results"):
            return None, "No results returned from check-gmail.live API"
        return data, None
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
        footer = f"\n\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

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
        full_message = f"📧 <b>Mail Check Results</b>\n•──────────────────────•\n\n{formatted_output}{footer}"

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
                        caption=f"📧 <b>Mail Check Results</b>\n•──────────────────────•\n\n✅ Checked {len(results)} emails.\n📄 File attached due to length.{footer}",
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
