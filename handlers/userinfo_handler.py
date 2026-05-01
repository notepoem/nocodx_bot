import requests
from telebot.types import Message, InputFile
from io import BytesIO
import html
import json
import re
import asyncio

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    async def fetch_info(bot, message: Message, target_type: str):
        wait_msg = await bot.reply_to(message, "⏳ Getting information, please wait...", parse_mode="HTML")

        identifier = None
        user_input = ""
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            user_input = parts[1].strip()

        if user_input:
            identifier = user_input
            if not identifier.startswith("@") and not identifier.lstrip("-").isdigit():
                 identifier = "@" + identifier
        elif message.reply_to_message:
            user = message.reply_to_message.from_user
            if target_type == "bot" and user.is_bot:
                identifier = f"@{user.username}" if user.username else str(user.id)
            elif target_type == "user":
                identifier = f"@{user.username}" if user.username else str(user.id)
        
        if not identifier:
            if target_type == "user":
                identifier = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)
            elif target_type == "group" and message.chat.type in ["group", "supergroup"]:
                identifier = f"@{message.chat.username}" if message.chat.username else str(message.chat.id)

        if not identifier:
            example = f"@{target_type}username"
            await bot.edit_message_text(f"ℹ️ Provide username/ID or reply to a message.\nExample: <code>{command_prefixes_list[0]}info {example}</code>", message.chat.id, wait_msg.message_id, parse_mode="HTML")
            return

        try:
            api_url = f"https://web-production-29d53.up.railway.app/api/get_user_info?username={identifier}"
            response = await asyncio.to_thread(requests.get, api_url, timeout=15)
            
            if response.status_code != 200:
                await bot.edit_message_text("❌ API Error: Could not fetch info.", message.chat.id, wait_msg.message_id)
                return

            data = response.json()
            
            final_msg = format_info_response(data, identifier, message)
            profile_pic_url = data.get('profile_picture', {}).get('url')
            await bot.delete_message(message.chat.id, wait_msg.message_id)

            if profile_pic_url and profile_pic_url.startswith("http"):
                try:
                    media_resp = await asyncio.to_thread(requests.get, profile_pic_url, timeout=15)
                    media_content = BytesIO(media_resp.content)
                    
                    if profile_pic_url.lower().endswith('.mp4') or 'video' in media_resp.headers.get('content-type', ''):
                        media_content.name = "profile.mp4"
                        await bot.send_video(message.chat.id, media_content, caption=final_msg, parse_mode="HTML", reply_to_message_id=message.message_id)
                    else:
                        media_content.name = "profile.jpg"
                        await bot.send_photo(message.chat.id, media_content, caption=final_msg, parse_mode="HTML", reply_to_message_id=message.message_id)
                except Exception as e:
                    print(f"Media Error: {e}")
                    await bot.send_message(message.chat.id, final_msg, parse_mode="HTML", reply_to_message_id=message.message_id)
            else:
                await bot.send_message(message.chat.id, final_msg, parse_mode="HTML", reply_to_message_id=message.message_id)

        except Exception as e:
            await bot.edit_message_text(f"❌ Error: {str(e)}", message.chat.id, wait_msg.message_id)

    def add_line(parts, label, value, is_code=True):
        if value and value != 'N/A' and str(value) != 'None':
            val_str = html.escape(str(value))
            # Convert label to bold Unicode
            label_map = {
                "Name": "𝗡𝗮𝗺𝗲", "Full Name": "𝗙𝘂𝗹𝗹 𝗡𝗮𝗺𝗲", "Username": "𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲",
                "User ID": "𝗨𝘀𝗲𝗿 𝗜𝗗", "Language": "𝗟𝗮𝗻𝗴𝘂𝗮𝗴𝗲", "Phone": "𝗣𝗵𝗼𝗻𝗲",
                "Bio": "𝗕𝗶𝗼", "Description": "𝗗𝗲𝘀𝗰𝗿𝗶𝗽𝘁𝗶𝗼𝗻", "Title": "𝗧𝗶𝘁𝗹𝗲",
                "Chat ID": "𝗖𝗵𝗮𝘁 𝗜𝗗", "Type": "𝗧𝘆𝗽𝗲", "Members": "𝗠𝗲𝗺𝗯𝗲𝗿𝘀",
                "Safety Status": "𝗦𝗮𝗳𝗲𝘁𝘆 𝗦𝘁𝗮𝘁𝘂𝘀", "Data Center": "𝗗𝗮𝘁𝗮 𝗖𝗲𝗻𝘁𝗲𝗿",
                "Status": "𝗦𝘁𝗮𝘁𝘂𝘀", "Last Online": "𝗟𝗮𝘀𝘁 𝗢𝗻𝗹𝗶𝗻𝗲", "Active Users": "𝗔𝗰𝘁𝗶𝘃𝗲 𝗨𝘀𝗲𝗿𝘀"
            }
            bold_label = label_map.get(label, label)
            if label == "Bio" or label == "Description": # Special handling for long text
                 clean_text = re.sub(r'<[^>]+>', '', str(value))
                 parts.append(f"• <b>{bold_label}:</b> <code>{html.escape(clean_text)}</code>")
            else:
                fmt_val = f"<code>{val_str}</code>" if is_code else val_str
                parts.append(f"• <b>{bold_label}:</b> {fmt_val}")

    def add_status_grid(parts, items):
        batch = []
        for label, val in items:
            if val is not None:
                emoji = "✅" if val else "❌"
                status = "Yes" if val else "No"
                batch.append(f"<b>{label}</b>: {emoji} {status}")
                if len(batch) == 2:
                    parts.append("• " + "  |  ".join(batch))
                    batch = []
        if batch:
            parts.append("• " + "  |  ".join(batch))

    def format_info_response(data, identifier, message):
        parts = []
        rtype = data.get('type')
        
        emoji_map = {'user': '👤', 'bot': '🤖', 'group': '👥', 'channel': '📢'}
        header = f"<b>{emoji_map.get(rtype, 'ℹ️')} {rtype.upper()} INFORMATION</b>"
        parts.append(header)
        parts.append(f"📎 <b>Identifier:</b> <code>{html.escape(identifier)}</code>\n")
        parts.append("•━━━━━ <b>BASIC INFO</b> ━━━━━•")
        
        if rtype in ['user', 'bot']:
            info = data.get('basic_info', {})
            add_line(parts, "Name", info.get('name'))
            add_line(parts, "Full Name", info.get('full_name'))
            add_line(parts, "Username", info.get('username'))
            add_line(parts, "User ID", info.get('user_id'))
            add_line(parts, "Language", info.get('language_code'))
            add_line(parts, "Phone", info.get('phone_number'))
            add_line(parts, "Bio", info.get('bio'))
            
            acct_status = data.get('account_status', {})
            if acct_status.get('is_bot') is not None:
                emoji = "🤖" if acct_status['is_bot'] else "❌"
                status_text = "Yes" if acct_status['is_bot'] else "No"
                parts.append(f"• <b>Bot:</b> {emoji} {status_text}")

        elif rtype in ['channel', 'group']:
            add_line(parts, "Title", data.get('title'))
            add_line(parts, "Username", data.get('username'))
            add_line(parts, "Chat ID", data.get('chat_id'))
            add_line(parts, "Type", data.get('entity_type'))
            add_line(parts, "Members", data.get('members_count'))

        parts.append("•━━━━━ <b>𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗦𝗧𝗔𝗧𝗨𝗦</b> ━━━━━•")
        status_items = []
        
        if rtype in ['user', 'bot']:
            s = data.get('account_status', {})
            status_items = [
                ('𝗣𝗿𝗲𝗺𝗶𝘂𝗺', s.get('is_premium')), ('𝗩𝗲𝗿𝗶𝗳𝗶𝗲𝗱', s.get('is_verified')),
                ('𝗙𝗿𝗼𝘇𝗲𝗻', s.get('is_frozen')), ('𝗗𝗲𝗹𝗲𝘁𝗲𝗱', s.get('is_deleted')),
                ('𝗦𝗰𝗮𝗺', s.get('is_scam')), ('𝗙𝗮𝗸𝗲', s.get('is_fake')),
                ('𝗥𝗲𝘀𝘁𝗿𝗶𝗰𝘁𝗲𝗱', s.get('is_restricted'))
            ]
        else:
            status_items = [
                ('𝗩𝗲𝗿𝗶𝗳𝗶𝗲𝗱', data.get('verified')), ('𝗦𝗰𝗮𝗺', data.get('scam')),
                ('𝗙𝗮𝗸𝗲', data.get('fake'))
            ]
            
        add_status_grid(parts, status_items)

        if rtype == 'bot':
            binfo = data.get('bot_info', {})
            if binfo:
                parts.append("•━━━━━ <b>BOT SPECIFIC</b> ━━━━━•")
                if binfo.get('is_bot_business') is not None:
                    emoji = "✅" if binfo['is_bot_business'] else "❌"
                    parts.append(f"• <b>Business Bot</b>: {emoji} {'Yes' if binfo['is_bot_business'] else 'No'}")
                add_line(parts, "Active Users", binfo.get('active_users'))

        if rtype in ['user', 'bot']:
            net = data.get('network_status', {})
            if any(net.values()):
                parts.append("•━━━━━ <b>𝗦𝗧𝗔𝗧𝗨𝗦</b> ━━━━━•")
                add_line(parts, "Data Center", net.get('data_center'))
                add_line(parts, "Status", net.get('status'))
                add_line(parts, "Last Online", net.get('last_online'))
        
        if rtype in ['channel', 'group']:
             add_line(parts, "Safety Status", data.get('safety_status'))
             if data.get('description'):
                parts.append("•━━━━━ <b>𝗗𝗘𝗦𝗖𝗥𝗜𝗣𝗧𝗜𝗢𝗡</b> ━━━━━•")
                clean_desc = re.sub(r'<[^>]+>', '', data['description'])
                parts.append(f"<code>{html.escape(clean_desc)}</code>")

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"
        parts.append(footer)
        return "\n".join(parts)

    # --- Command Registrations ---
    @custom_command_handler("usr", "user")
    async def handle_user(message):
        if check_usage_limit and not await check_usage_limit(message, "Userinfo"): return
        await fetch_info(bot, message, "user")

    @custom_command_handler("bot")
    async def handle_bot(message):
        if check_usage_limit and not await check_usage_limit(message, "Userinfo"): return
        await fetch_info(bot, message, "bot")

    @custom_command_handler("grp", "group")
    async def handle_group(message):
        if check_usage_limit and not await check_usage_limit(message, "Userinfo"): return
        await fetch_info(bot, message, "group")

    @custom_command_handler("cnnl", "channel")
    async def handle_channel(message):
        if check_usage_limit and not await check_usage_limit(message, "Userinfo"): return
        await fetch_info(bot, message, "channel")

    @custom_command_handler("info")
    async def handle_info(message):
        if check_usage_limit and not await check_usage_limit(message, "Userinfo"): return
        
        parts = message.text.split(maxsplit=1)
        target = "user" # Default
        
        if len(parts) > 1:
            arg = parts[1].lower()
            if arg.endswith("bot"): target = "bot"
            elif "channel" in arg: target = "channel"
            elif "group" in arg: target = "group"

        await fetch_info(bot, message, target)
