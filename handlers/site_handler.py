import aiohttp
import asyncio
import re
from urllib.parse import urlparse
import html 
from telebot.apihelper import ApiTelegramException

# API Endpoint
SITE_LOOKUP_API = "https://gateway-lookup.vercel.app/api/gate?site={}&format=json"

def extract_urls(text):
    """Extract URLs from text using regex."""
    # Find full URLs
    urls = re.findall(r'(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?)', text)
    # Also find domains without http and add https
    domains = re.findall(r'(?<![htps:/])\b([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?)\b', text)
    for d in domains:
        if not any(d in u for u in urls):
            urls.append(f"https://{d}")
    return list(dict.fromkeys(urls)) # Remove duplicates

def format_site_result(data, scan_time):
    """Format the lookup result into a beautiful requested aesthetic."""
    url = data.get("url", "N/A")
    gateways = ", ".join(data.get("possible_payment_gateways", [])) or "None Detected"
    cms = ", ".join(data.get("cms", [])) or "None Detected"
    platforms = ", ".join(data.get("platforms", [])) or "None Detected"
    
    # Captcha
    captcha_dict = data.get("captcha", {})
    captcha = ", ".join(captcha_dict.keys()) if captcha_dict else "None Detected"
    
    # Cloudflare
    cf_detected = data.get("cloudflare", False)
    cf_services = data.get("cloudflare_services", {})
    cloudflare = "Cloudflare Detected" if cf_detected else "Not Detected"
    if cf_services:
        cf_details = "\n            ".join([f"{k}: {v}" for k, v in cf_services.items()])
        cloudflare += f"\n            {cf_details}"
    
    # Security
    secure_3d = data.get("secure_3d", False)
    security = "3D Secure Found ✓" if secure_3d else "No 3D Secure Detected"
    
    # GraphQL
    graphql_detected = data.get("graphql", False)
    graphql = "GraphQL Detected ✅" if graphql_detected else "No GraphQL Detected ❌"
    
    # SSL
    ssl = data.get("ssl", {})
    ssl_issuer = ssl.get("issuer", "N/A")
    ssl_subject = ssl.get("subject", "N/A")
    ssl_valid = "✅" if ssl.get("is_valid") else "❌"
    
    # Domain Whois
    whois = data.get("domain_whois", {})
    domain_name = whois.get("domain", urlparse(url).netloc)
    registrar = whois.get("registrar", "N/A")
    created = whois.get("creation_date", "N/A")
    expires = whois.get("expiration_date", "N/A")
    ns_list = whois.get("nameservers", [])
    ns = ", ".join(ns_list) if isinstance(ns_list, list) else str(ns_list)
    
    # IP Information
    ip_info = data.get("ip_information", {})
    ip_addr = ip_info.get("ip", "N/A")
    country = ip_info.get("country", "N/A")
    city = ip_info.get("city", "N/A")
    isp = ip_info.get("isp", "N/A")
    asn = ip_info.get("as", "N/A")

    # The manual scan_time might be more accurate if API scan_time is missing, but let's use API one if present
    api_scan_time = data.get("scan_time", scan_time)

    return (
        f"◇━━〔 𝑳𝒐𝒐𝒌𝒖𝒑 ⋆༺𓆩☠︎︎𓆪༻⋆ 𝑹𝒆𝒔𝒖𝒍𝒕𝒔 〕━━◇\n"
        f"[✘] 𝐒𝐢𝐭𝐞 ➵ <code>{html.escape(url)}</code>\n"
        f"[✘] 𝐆𝐚𝐭𝐞𝐰𝐚𝐲𝐬 ➵ <code>{html.escape(gateways)}</code>\n"
        f"[✘] 𝐂𝐌𝐒 ➵ <code>{html.escape(cms)}</code>\n"
        f"[✘] 𝐏𝐥𝐚𝐭𝐟𝐨𝐫𝐦𝐬 ➵ <code>{html.escape(platforms)}</code>\n"
        f"――――――――――――――――\n"
        f"[✘] 𝐂𝐚𝐩𝐭𝐜𝐡𝐚 ➵ <code>{html.escape(captcha)}</code>\n"
        f"[✘] 𝐂𝐥𝗼𝐮𝐝𝐟𝐥𝐚𝐫𝐞 ➵ <code>{html.escape(cloudflare)}</code>\n"
        f"[✘] 𝐒𝐞𝐜𝐮𝐫𝐢𝐭𝐲 ➵ <code>{html.escape(security)}</code>\n"
        f"[✘] 𝐆𝐫𝐚𝐩𝐡𝐐𝐋 ➵ <code>{html.escape(graphql)}</code>\n"
        f"――――――――――――――――\n"
        f"🔐 𝑺𝑺𝑳 𝑫𝒆𝒕𝒂𝒊𝒍𝒔:\n"
        f"   ├─ 𝐈𝐬𝐬𝐮𝐞𝐫: <code>{html.escape(ssl_issuer)}</code>\n"
        f"   ├─ 𝐒𝐮𝐛𝐣𝐞𝐜𝐭: <code>{html.escape(ssl_subject)}</code>\n"
        f"   └─ 𝐕𝐚𝐥𝐢𝐝: {ssl_valid}\n"
        f"――――――――――――――――\n"
        f"[✘] 𝑫𝒐𝒎𝒂𝒊𝒏: <code>{html.escape(domain_name)}</code>\n"
        f"            Registrar: <code>{html.escape(registrar)}</code>\n"
        f"            Created: <code>{html.escape(created)}</code>\n"
        f"            Expires: <code>{html.escape(expires)}</code>\n"
        f"            Nameservers: <code>{html.escape(ns)}</code>\n"
        f"――――――――――――――――\n"
        f"[✘] 𝑰𝑷 𝑰𝒏𝒇𝒐: <code>{html.escape(ip_addr)}</code>\n"
        f"            Country: <code>{html.escape(country)}</code>\n"
        f"            City: <code>{html.escape(city)}</code>\n"
        f"            ISP: <code>{html.escape(isp)}</code>\n"
        f"            ASN: <code>{html.escape(asn)}</code>\n"
        f"――――――――――――――――\n"
        f"⚡ 𝑺𝒄𝒂𝒏 𝑻𝒊𝒎𝒆: {api_scan_time}s"
    )

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("site")
    async def handle_site_command(message):
        if check_usage_limit and not await check_usage_limit(message, "Site"):
            return
        
        content = message.text
        if message.reply_to_message:
            content += "\n" + (message.reply_to_message.text or "")
        
        found_urls = extract_urls(content)
        if not found_urls:
            await bot.reply_to(message, "❗ Please provide one or more **valid website URLs** or reply to a message containing URLs.", parse_mode="Markdown")
            return
            
        # Limit mass check to 10
        valid_urls = found_urls[:10]
        
        sent_message = await bot.reply_to(message, f"🔄 **Checking {len(valid_urls)} site(s)... Please wait.**", parse_mode="Markdown")
        if not sent_message:
            return

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"


        async def run_sequential_checks():
            for index, url in enumerate(valid_urls):
                try:
                    await bot.edit_message_text(
                        chat_id=sent_message.chat.id,
                        message_id=sent_message.message_id,
                        text=f"🔄 **Checking site {index + 1} of {len(valid_urls)}:** <code>{url}</code>",
                        parse_mode="HTML"
                    )
                except:
                    pass

                import time as t
                start_time = t.time()
                result = await lookup_site(url)
                scan_time = round(t.time() - start_time, 2)

                if result.get("error"):
                    response_text = f"❌ <b>𝗨𝗥𝗟:</b> <code>{html.escape(url)}</code>\n"
                    response_text += f"❌ <b>𝗘𝗿𝗿𝗼𝗿:</b> <code>{html.escape(result['error'])}</code>"
                else:
                    response_text = format_site_result(result["data"], scan_time)
                
                final_response = f"{response_text}\n{footer}"
                
                await bot.reply_to(message, final_response, parse_mode="HTML")
                
                # Add a small delay between lookups for stability
                if index < len(valid_urls) - 1:
                    await asyncio.sleep(2)

            try:
                await bot.delete_message(chat_id=sent_message.chat.id, message_id=sent_message.message_id)
            except:
                pass

        await run_sequential_checks()
        loop.close()

async def lookup_site(url: str) -> dict:
    lookup_url = SITE_LOOKUP_API.format(url)
    headers = { "User-Agent": "Mozilla/5.0 (DefensiveTool/1.0)" }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(lookup_url, headers=headers, timeout=30) as res:
                if res.status == 200:
                    try:
                        data = await res.json()
                        return {"url": url, "data": data}
                    except:
                        # Fallback for unexpected format if API changed but still 200
                        return {"url": url, "error": "API returned invalid JSON format."}
                else:
                    return {"url": url, "error": f"API call failed: HTTP {res.status}"}
    except asyncio.TimeoutError:
        return {"url": url, "error": "API call timed out."}
    except Exception as e:
        return {"url": url, "error": str(e)}
