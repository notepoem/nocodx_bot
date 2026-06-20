import requests
import json
import re
import time
import asyncio

number_cooldowns = {}
COOLDOWN_SECONDS = 60  # 1 minute

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @custom_command_handler("bmb", "bomb")
    async def handle_bomb(message):
        if check_usage_limit and not await check_usage_limit(message, "Bomb"):
            return
        chat_id = message.chat.id
        user_id = message.from_user.id if message.from_user else 0

        if not message.text:
            return

        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             args = " ".join(parts_split[1:]).strip()
        else:
             args = ""

        if not args:
            help_text = f"""❓ <b>SMS Bomber ব্যবহারের নিয়ম:</b>

<code>{command_prefixes_list[0]}bmb [ফোন নম্বর]</code>
<code>{command_prefixes_list[1]}bomb [ফোন নম্বর]</code>

<b>উদাহরণ:</b>
<code>{command_prefixes_list[0]}bmb 01xxxxxxxx</code>
<code>{command_prefixes_list[1]}bomb 01xxxxxxxx</code>"""
            await bot.reply_to(message, help_text, parse_mode="HTML")
            return

        phone_number = args.split()[0]
        amount = 1  # Amount is now fixed to 1

        if not re.match(r'^(\+880|880|0)?1[3-9]\d{8}$', phone_number):
            await bot.reply_to(message, "❌ সঠিক বাংলাদেশি ফোন নম্বর দিন! (উদাহরণ: 01xxxxxxxx)", parse_mode="HTML")
            return

        normalized_number = phone_number[-11:]
        current_time = time.time()
        if normalized_number in number_cooldowns:
            last_used_time = number_cooldowns[normalized_number]
            time_elapsed = current_time - last_used_time
            remaining_cooldown = COOLDOWN_SECONDS - time_elapsed
            
            if remaining_cooldown > 0:
                minutes = int(remaining_cooldown // 60)
                seconds = int(remaining_cooldown % 60)
                await bot.reply_to(message, 
                    f"⏳ <b>এই নম্বর এখনও Cooldown এ আছে!</b>\n\n"
                    f"📱 <code>{normalized_number}</code>\n\n"
                    f"⏰ <b>অপেক্ষা করুন:</b> <code>{minutes}মি {seconds}সে</code>\n\n"
                    f"<i>নিরাপত্তার জন্য একই নম্বর ১ মিনিটের মধ্যে দুইবার ব্যবহার করা যায় না।</i>",
                    parse_mode="HTML")
                return
        
        number_cooldowns[normalized_number] = current_time

        processing_msg = await bot.reply_to(message, f"🔄 <b>{normalized_number}</b> নম্বরে রিকোয়েস্ট পাঠানো হচ্ছে...\n\n⏳ <i>দয়া করে ২-৩ মিনিট অপেক্ষা করুন...</i>", parse_mode="HTML")

        try:
            url = "https://noob-bmbr.vercel.app/bomb"
            payload = {
                "number": normalized_number,
                "amount": amount
            }
            headers = {
                'Content-Type': 'application/json'
            }

            response = await asyncio.to_thread(requests.post, url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()

            data = response.json()

            successful_requests = data.get('successful_requests', 0)
            total_requests = data.get('total_requests_attempted', 0)

            api_44_bonus = 0
            details = data.get('details', [])
            
            for api_detail in details:
                if api_detail.get('api_name') == 'api_44' and api_detail.get('status') == 'success':
                    api_44_bonus = 50
                    break

            successful_requests_with_bonus = successful_requests + api_44_bonus

            if total_requests > 0:
                success_rate = (successful_requests_with_bonus / total_requests) * 100
            else:
                success_rate = 0

            success_count = sum(1 for api in details if api.get('status') == 'success')
            failed_count = sum(1 for api in details if api.get('status') == 'failed')
            error_count = sum(1 for api in details if api.get('status') == 'error')

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"\n\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

            result_message = f"""✅ <b>রিকোয়েস্ট সম্পন্ন হয়েছে!</b>

📱 <b>𝗣𝗵𝗼𝗻𝗲 𝗡𝘂𝗺𝗯𝗲𝗿:</b> <code>{normalized_number}</code>
🎯 <b>𝗔𝗺𝗼𝘂𝗻𝘁:</b> <code>{amount}</code>

📊 <b>𝗥𝗲𝘀𝘂𝗹𝘁𝘀:</b>
├─ 🟢 <b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀:</b> <code>{success_count}</code>
├─ 🔴 <b>𝗙𝗮𝗶𝗹𝗲𝗱:</b> <code>{failed_count}</code>
├─ ⚠️ <b>𝗘𝗿𝗿𝗼𝗿:</b> <code>{error_count}</code>
└─ 📈 <b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀 𝗥𝗮𝘁𝗲:</b> <code>{success_rate:.1f}%</code>

🔢 <b>𝗧𝗼𝘁𝗮𝗹 𝗔𝗣𝗜 𝗖𝗮𝗹𝗹𝘀:</b> <code>{total_requests}</code>
✅ <b>𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹 𝗔𝗣𝗜 𝗖𝗮𝗹𝗹𝘀:</b> <code>{successful_requests_with_bonus}</code>"""

            if api_44_bonus > 0:
                result_message += f"\n\n🎉 <b>𝗕𝗼𝗻𝘂𝘀:</b> api_44 successful <code>+{api_44_bonus}</code> added!"

            await bot.edit_message_text(
                result_message + footer, 
                chat_id=chat_id, 
                message_id=processing_msg.message_id, 
                parse_mode="HTML"
            )

        except requests.exceptions.Timeout:
            await bot.edit_message_text(
                "⏰ <b>টাইমআউট!</b> API সার্ভার খুব ধীর বা অনুপলব্ধ।", 
                chat_id=chat_id, 
                message_id=processing_msg.message_id, 
                parse_mode="HTML"
            )
        except requests.exceptions.RequestException as e:
            await bot.edit_message_text(
                f"❌ <b>নেটওয়ার্ক ত্রুটি!</b>\n\n<code>{str(e)}</code>", 
                chat_id=chat_id, 
                message_id=processing_msg.message_id, 
                parse_mode="HTML"
            )
        except json.JSONDecodeError:
            await bot.edit_message_text(
                "❌ <b>API রেসপন্স পার্স করতে সমস্যা!</b> সার্ভার থেকে অবৈধ JSON পেয়েছি।", 
                chat_id=chat_id, 
                message_id=processing_msg.message_id, 
                parse_mode="HTML"
            )
        except KeyError as e:
            await bot.edit_message_text(
                f"❌ <b>API রেসপন্স ফরম্যাট সমস্যা!</b>\n\nঅনুপস্থিত ফিল্ড: <code>{str(e)}</code>", 
                chat_id=chat_id, 
                message_id=processing_msg.message_id, 
                parse_mode="HTML"
            )
        except Exception as e:
            await bot.edit_message_text(
                f"❌ <b>অপ্রত্যাশিত ত্রুটি!</b>\n\n<code>{str(e)}</code>", 
                chat_id=chat_id, 
                message_id=processing_msg.message_id, 
                parse_mode="HTML"
            )
