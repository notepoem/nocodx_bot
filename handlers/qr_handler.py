import os
import re
import cv2
import numpy as np
import qrcode
import requests
from PIL import Image, ImageDraw
import html
from telebot import types
import asyncio

user_data = {}

CACHE_DIR = os.path.join(os.getcwd(), "cache", "qr")
os.makedirs(CACHE_DIR, exist_ok=True)

def generate_custom_qr(data, logo_path=None):
    # Configurations for High Quality
    BOX_SIZE = 50 
    BORDER = 2
    
    # Standard Colors
    QR_COLOR = "black"
    BG_COLOR = "white"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=BOX_SIZE,
        border=BORDER,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Generate basic black/white QR
    img = qr.make_image(fill_color=QR_COLOR, back_color=BG_COLOR).convert('RGB')
    
    # --- Logo Integration ---
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        
        qr_width, qr_height = img.size
        # Reduce logo size to 20% (1/5) to ensure scannability for dense data
        logo_size = qr_width // 5
        
        logo_container_size = logo_size
        
        # Consistent Border
        # Thick white 'halo' to separate text from logo
        border_width = int(logo_size * 0.05) 
        if border_width < 10: border_width = 10 
        
        # Container
        final_logo_comp = Image.new("RGBA", (logo_container_size, logo_container_size), (0,0,0,0))
        draw_comp = ImageDraw.Draw(final_logo_comp)
        
        # 1. Background Circle (White) - Cleans up the QR modules behind it
        draw_comp.ellipse((0, 0, logo_container_size, logo_container_size), fill="white")
        
        # 2. Outer Ring (Black) - To match the QR code modules
        # A thin black ring to define the circle cleanly
        ring_thickness = border_width // 4
        if ring_thickness < 2: ring_thickness = 2
        draw_comp.ellipse((0, 0, logo_container_size, logo_container_size), outline="black", width=ring_thickness)
        
        # 3. Prepare Logo
        inner_size = logo_container_size - (border_width * 2)
        
        # Crop square
        w, h = logo.size
        min_dim = min(w, h)
        logo = logo.crop(((w-min_dim)//2, (h-min_dim)//2, (w+min_dim)//2, (h+min_dim)//2))
        
        # Resize 
        logo = logo.resize((inner_size, inner_size), Image.Resampling.LANCZOS)
        
        # Circular Mask
        mask = Image.new("L", (inner_size, inner_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, inner_size, inner_size), fill=255)
        
        # Paste Logo
        offset = (logo_container_size - inner_size) // 2
        final_logo_comp.paste(logo, (offset, offset), mask=mask)
        
        # Paste onto QR
        pos = ((qr_width - logo_container_size) // 2, (qr_height - logo_container_size) // 2)
        img.paste(final_logo_comp, pos, mask=final_logo_comp)

    # Resize if too large (Telegram limit safety)
    max_size = 2048
    if img.size[0] > max_size or img.size[1] > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"qr_{np.random.randint(1000)}.png")
    img.save(path)
    return path

def register(bot, custom_command_handler, COMMAND_PREFIXES, check_usage_limit=None):

    @custom_command_handler("qr")
    async def handle_qr(message):
        if check_usage_limit and not await check_usage_limit(message, "Qr"):
            return
        if message.reply_to_message and message.reply_to_message.photo:
            sent_msg = await bot.reply_to(message, "🔍 <b>Scanning QR Code...</b>", parse_mode="HTML")
            try:
                file_info = await bot.get_file(message.reply_to_message.photo[-1].file_id)
                downloaded_file = await bot.download_file(file_info.file_path)

                # Online QR Scan API (GoQR.me)
                api_url = "https://api.qrserver.com/v1/read-qr-code/"
                files = {"file": ("qr_image.jpg", downloaded_file)}
                response = await asyncio.to_thread(requests.post, api_url, files=files)
                response.raise_for_status()
                json_data = response.json()

                data = None
                if json_data and isinstance(json_data, list) and json_data[0]["symbol"]:
                    symbol = json_data[0]["symbol"][0]
                    if symbol["data"]:
                        data = symbol["data"]

                if data:
                    data = data.strip()
                    user = message.from_user
                    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                    footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
                    if data.startswith("http"):
                        display_text = re.sub(r'^https?://', '', data)
                        data_display = f'<a href="{html.escape(data)}">{html.escape(display_text)}</a>'
                    else:
                        data_display = f'<code>{html.escape(data)}</code>'
                    response_text = f"✅ <b>𝗤𝗥 𝗖𝗼𝗱𝗲 𝗦𝗰𝗮𝗻𝗻𝗲𝗱!</b>\n\n📝 <b>𝗗𝗮𝘁𝗮:</b>\n{data_display}\n{footer}"
                    markup = types.InlineKeyboardMarkup()
                    if data.startswith("http"):
                        markup.add(types.InlineKeyboardButton("🌐 Open Link", url=data))
                    await bot.edit_message_text(response_text, message.chat.id, sent_msg.message_id, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
                else:
                    await bot.edit_message_text("❌ <b>No valid QR code found in this image.</b>", message.chat.id, sent_msg.message_id, parse_mode="HTML")
            except Exception as e:
                await bot.edit_message_text(f"❌ <b>Error:</b> {str(e)}", message.chat.id, sent_msg.message_id, parse_mode="HTML")
            return
        cmd_parts = message.text.split(None, 1)
        if len(cmd_parts) < 2:
            await bot.reply_to(message, "❌ <b>Usage Rules:</b>\n\n1. <b>Scan:</b> Reply to an image with <code>/qr</code>.\n2. <b>Generate:</b> Type <code>/qr [your text]</code>.", parse_mode="HTML")
            return

        text_to_encode = cmd_parts[1]
        user_data[message.from_user.id] = {'text': text_to_encode}

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Yes (Add Logo)", callback_data="qr_logo_yes"),
            types.InlineKeyboardButton("❌ No (Simple QR)", callback_data="qr_logo_no")
        )

        await bot.reply_to(message, f"🎨 <b>𝗧𝗲𝘅𝘁:</b> <code>{html.escape(text_to_encode)}</code>\n\nDo you want to add a logo to this QR code?", parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("qr_logo_"))
    async def handle_callback(call):
        user_id = call.from_user.id
        if user_id not in user_data:
            await bot.answer_callback_query(call.id, "Session expired! Please run the command again.")
            return

        if call.data == "qr_logo_no":
            await bot.edit_message_text("⚙️ <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗶𝗻𝗴 𝗦𝗶𝗺𝗽𝗹𝗲 𝗤𝗥...</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
            qr_path = generate_custom_qr(user_data[user_id]['text'])
            user = call.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
            with open(qr_path, 'rb') as photo:
                await bot.send_photo(call.message.chat.id, photo, caption=f"✅ <b>𝗦𝗶𝗺𝗽𝗹𝗲 𝗤𝗥 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱!</b>\n{footer}", parse_mode="HTML")
            if os.path.exists(qr_path): os.remove(qr_path)
            del user_data[user_id]

        elif call.data == "qr_logo_yes":
            await bot.edit_message_text("🖼️ <b>Send the logo image (1:1 ratio preferred)</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
            user_data[user_id]['state'] = 'waiting_logo'

    @bot.message_handler(func=lambda message: message.from_user.id in user_data and user_data[message.from_user.id].get('state') == 'waiting_logo')
    async def process_logo_step(message):
        user_id = message.from_user.id

        if not message.photo:
            await bot.reply_to(message, "❌ Please send a photo! Process cancelled.")
            if user_id in user_data: del user_data[user_id]
            return

        sent_msg = await bot.reply_to(message, "⚙️ <b>Processing QR with Logo...</b>", parse_mode="HTML")

        file_info = await bot.get_file(message.photo[-1].file_id)
        logo_bytes = await bot.download_file(file_info.file_path)
        logo_path = os.path.join(CACHE_DIR, f"logo_{user_id}.png")

        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(logo_path, "wb") as f:
            f.write(logo_bytes)

        try:
            qr_path = generate_custom_qr(user_data[user_id]['text'], logo_path)
            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
            with open(qr_path, 'rb') as photo:
                await bot.send_photo(message.chat.id, photo, caption=f"✨ <b>𝗖𝘂𝘀𝘁𝗼𝗺 𝗟𝗼𝗴𝗼 𝗤𝗥 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱!</b>\n{footer}", parse_mode="HTML")
            if os.path.exists(qr_path): os.remove(qr_path)
        except Exception as e:
            await bot.reply_to(message, f"❌ Error: {str(e)}")
        finally:
            if os.path.exists(logo_path): os.remove(logo_path)
            if user_id in user_data: del user_data[user_id]