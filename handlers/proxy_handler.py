import requests
import time
import concurrent.futures
import io
import os
from telebot.types import InputFile
import asyncio

def check_one_proxy(proxy_input):
    proxy_input = proxy_input.strip()
    if not proxy_input:
        return None

    for prefix in ["http://", "https://", "socks4://", "socks5://", "socks://"]:
        if proxy_input.lower().startswith(prefix):
            proxy_input = proxy_input[len(prefix):]

    parts = proxy_input.split(':')
    user = pwd = ip = port = ""

    if len(parts) == 2:
        ip, port = parts[0], parts[1]
    elif len(parts) == 4:
        ip, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
    else:
        return {"status": False, "input": proxy_input, "msg": "Invalid Format"}

    ip_port = f"{ip}:{port}"

    for proto in ["socks5", "socks4", "http"]:
        if user and pwd:
            proxy_url = f"{proto}://{user}:{pwd}@{ip}:{port}"
        else:
            proxy_url = f"{proto}://{ip}:{port}"

        proxies = {"http": proxy_url, "https": proxy_url}
        start_time = time.time()

        try:
            response = requests.get("http://ip-api.com/json/", proxies=proxies, timeout=5)
            latency = round((time.time() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "fail":
                    return {
                        "status": True,
                        "protocol": proto.upper(),
                        "input": proxy_input,
                        "latency": latency,
                        "country": "Unknown",
                        "isp": "Unknown",
                        "ip": ip_port,
                    }
                return {
                    "status": True,
                    "protocol": proto.upper(),
                    "input": proxy_input,
                    "latency": latency,
                    "country": data.get("country", "Unknown"),
                    "isp": data.get("isp", "Unknown"),
                    "ip": data.get("query", ip_port),
                    "original_ip": ip_port,
                }
        except Exception:
            continue

    return {"status": False, "input": proxy_input, "msg": "Connection Failed"}

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("proxy", "px")
    async def handle_proxy_check(message):
        if check_usage_limit and not await check_usage_limit(message, "Proxy"):
            return
            
        proxy_lines = []
        
        if message.reply_to_message and message.reply_to_message.document:
            doc = message.reply_to_message.document
            if doc.mime_type and "text" in doc.mime_type or doc.file_name.endswith(".txt"):
                try:
                    file_info = await bot.get_file(doc.file_id)
                    downloaded = await bot.download_file(file_info.file_path)
                    content = downloaded.decode('utf-8', errors='ignore')
                    proxy_lines = content.splitlines()
                except Exception as e:
                    await bot.reply_to(message, f"❌ Failed to read file: {e}")
                    return
            else:
                await bot.reply_to(message, "⚠️ Please reply to a <b>Text File</b> (.txt).", parse_mode="HTML")
                return

        elif message.reply_to_message and message.reply_to_message.text:
            proxy_lines = message.reply_to_message.text.splitlines()
            
        else:
            args = message.text.split(maxsplit=1)
            if len(args) > 1:
                proxy_lines = args[1].splitlines()
        
        proxy_lines = [line.strip() for line in proxy_lines if line.strip()]
        
        if not proxy_lines:
            await bot.reply_to(message, 
                "⚠️ <b>Proxy Checker Usage:</b>\n\n"
                "1. <b>Single/List:</b> <code>/proxy IP:Port</code> (lines)\n"
                "2. <b>Reply:</b> Reply <code>/proxy</code> to a text message or <b>.txt file</b>.\n\n"
                "<i>Supported Formats:</i> <code>IP:Port</code> or <code>IP:Port:User:Pass</code>\n"
                "<i>Auto-detects: SOCKS5, SOCKS4, HTTP</i>",
                parse_mode="HTML"
            )
            return
            
        status_msg = await bot.reply_to(message, f"🔄 <b>Processing...</b>\nChecking {len(proxy_lines)} proxies.", parse_mode="HTML")
        
        results = []
        working = 0
        dead = 0
        MAX_THREADS = 15 
        start_ts = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            future_to_proxy = {executor.submit(check_one_proxy, p): p for p in proxy_lines}
            total = len(proxy_lines)
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_proxy):
                res = future.result()
                completed += 1
                
                if total > 20 and completed % 10 == 0:
                    try:
                        await bot.edit_message_text(f"🔄 <b>Checking...</b> ({completed}/{total})", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                    except: pass
                
                if res:
                    results.append(res)
                    if res['status']:
                        working += 1
                    else:
                        dead += 1
        
        duration = round(time.time() - start_ts, 1)
        
        output_lines = []
        output_lines.append(f"🛡 <b>Proxy Check Results</b>")
        output_lines.append(f"⏱ Time: {duration}s | Total: {len(proxy_lines)}")
        output_lines.append(f"✅ Live: {working} | 🔴 Dead: {dead}\n")
        output_lines.append(f"<b>--- ✅ Working Proxies ---</b>")
        live_proxies = [r for r in results if r['status']]
        dead_proxies = [r for r in results if not r['status']]
        
        if not live_proxies:
            output_lines.append("<i>None</i>")
        else:
            for p in live_proxies:
                flag = "🏳️"
                ctry = p.get('country', "Unknown")
                lat = p.get('latency', 0)
                proto = p.get('protocol', 'HTTP')
                lat_icon = "🟢" if lat < 1000 else "🟡"
                output_lines.append(f"{lat_icon} <code>{p['input']}</code>")
                output_lines.append(f"   └ [{proto}] {ctry} - {lat}ms")
        
        output_lines.append(f"\n<b>--- 🔴 Dead Proxies ---</b>")
        if not dead_proxies:
            output_lines.append("<i>None</i>")
        else:
             for p in dead_proxies:
                 output_lines.append(f"❌ <code>{p['input']}</code> ({p.get('msg', 'Dead')})")

        full_text = "\n".join(output_lines)
        
        try:
            if len(full_text) > 4000:
                file_io = io.BytesIO(full_text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "").encode('utf-8'))
                file_io.name = f"proxy_check_{message.message_id}.txt"
                await bot.delete_message(message.chat.id, status_msg.message_id) # Delete "Checking..."

                caption = (f"🛡 <b>Proxy Check Complete</b>\n"
                           f"✅ Live: {working}\n"
                           f"🔴 Dead: {dead}\n"
                           f"⏱ {duration}s\n\n"
                           f"📂 <i>Result too long, sent as file.</i>")
                
                await bot.send_document(message.chat.id, file_io, caption=caption, parse_mode="HTML")
            else:
                await bot.edit_message_text(full_text, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="HTML")
                
        except Exception as e:
            await bot.reply_to(message, f"❌ Error sending results: {e}")