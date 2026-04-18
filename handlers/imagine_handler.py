import requests
from urllib.parse import quote_plus
from telebot import types
import asyncio

BASE_URL = "https://deepai-img.vercel.app/api"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit):

    # Extended Models List
    MODELS = {
        # Base Models
        "deepai": {"name": "🎨 DeepAI", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "deepai"},
        "anifun": {"name": "👾 Anifun", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "anifun"},
        "flux": {"name": "🔮 Flux", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "bytes", "endpoint": "flux"},
        "freegen": {"name": "� FreeGen", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "bytes", "endpoint": "freegen"},
        "gen": {"name": "✨ Gen", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "gen"},
        "hidream": {"name": "💭 HiDream", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "bytes", "endpoint": "hidream"},
        "notegpt": {"name": "📝 NoteGPT", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "notegpt"},
        "venice": {"name": "🎭 Venice", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "bytes", "endpoint": "venice"},
        "visualgpt": {"name": "�️ VisualGPT", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "visualgpt"},
        "zimage": {"name": "🌟 Zimage", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "bytes", "endpoint": "zimage"},
        "imagegpt": {"name": "🤖 ImageGPT", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "imagegpt"},

        # VisualGPT Variants
        "vg_nano": {"name": "🍌 VG Nano", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/nano"},
        "vg_gempix": {"name": "💎 VG Gempix", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/gempix"},
        "vg_seedream4": {"name": "🌊 VG SD 4.0", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/seedream4"},
        "vg_seedream45": {"name": "🌊 VG SD 4.5", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/seedream45"},
        "vg_flux_dev": {"name": "🔮 VG Flux Dev", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/flux-dev"},
        "vg_flux_pro": {"name": "🔮 VG Flux Pro", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/flux-pro"},
        "vg_qwen": {"name": "👁️ VG Qwen", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/qwen"},
        "vg_minimax": {"name": "👁️ VG Minimax", "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"], "type": "json", "endpoint": "vg/minimax"},
        
        "nsfw": {
            "name": "🔞 NSFW",
            "ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
            "type": "sse",
            "endpoint": "https://my-x-img.vercel.app/api/nsfw", # Full URL as endpoint for custom handling
            "custom": True
        }
    }

    async def get_prompt_and_image(message):
        parts_split = message.text.strip().split()
        prompt = " ".join(parts_split[1:]).strip() if len(parts_split) > 1 else ""
        
        image_url = None
        if message.photo:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        elif message.reply_to_message:
            if not prompt:
                prompt = message.reply_to_message.text or message.reply_to_message.caption or ""
            if message.reply_to_message.photo:
                photo = message.reply_to_message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
                image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        return prompt, image_url

    @custom_command_handler("imagine", "img")
    async def handle_imagine(message):
        if check_usage_limit and not await check_usage_limit(message, "Imagine"):
            return
        
        prompt, _ = await get_prompt_and_image(message)
        if not prompt:
            await bot.reply_to(
                message,
                f"❓ Usage: `{command_prefixes_list[0]}imagine [prompt]`\n"
                f"Example: `{command_prefixes_list[0]}imagine beautiful sunset`",
                parse_mode="Markdown")
            return

        await show_model_selection(message, prompt, "imagine")

    @custom_command_handler("edit")
    async def handle_edit(message):
        if check_usage_limit and not await check_usage_limit(message, "Imagine"):
            return
            
        prompt, image_url = await get_prompt_and_image(message)
        if not image_url:
             await bot.reply_to(message, "⚠️ Please reply to an image or send an image with `/edit` to use image-to-image functions.")
             return
             
        if not prompt:
             await bot.reply_to(message, "❓ Please provide a prompt for editing.\nExample: `/edit make it a winter scene`")
             return

        await show_model_selection(message, prompt, "edit")

    async def show_model_selection(message, prompt, mode, edit_msg_id=None):
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        if mode == "edit":
             btns = [
                types.InlineKeyboardButton(MODELS["notegpt"]["name"], callback_data="imagine_m_e_notegpt"),
            ]
        else:
            # Show all models
            btns = [types.InlineKeyboardButton(v["name"], callback_data=f"imagine_m_i_{k}") for k, v in MODELS.items()]
            
        markup.add(*btns)

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name or str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
        
        title = "𝗜𝗺𝗮𝗴𝗶𝗻𝗲" if mode == "imagine" else "𝗘𝗱𝗶𝘁"
        text = f"🖼️ <b>{title}:</b> {prompt}\n\n👇 <b>𝗦𝗲𝗹𝗲𝗰𝘁 𝗮 𝗠𝗼𝗱𝗲𝗹:</b>\n{footer}"
        
        if edit_msg_id:
            await bot.edit_message_text(text, message.chat.id, edit_msg_id, reply_markup=markup, parse_mode="HTML")
        else:
            await bot.reply_to(message, text, reply_markup=markup, parse_mode="HTML")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("imagine_"))
    async def handle_imagine_callback(call):
        data = call.data.split("_")
        mode_prefix = data[1] # 'm' for model, 'g' for gen, 'back' for back
        
        async def get_current_info():
            text = call.message.text or call.message.caption or ""
            prompt = ""
            if "𝗜𝗺𝗮𝗴𝗶𝗻𝗲:" in text:
                prompt = text.split("𝗜𝗺𝗮𝗴𝗶𝗻𝗲:", 1)[1].split("\n\n", 1)[0].strip()
            elif "𝗘𝗱𝗶𝘁:" in text:
                prompt = text.split("𝗘𝗱𝗶𝘁:", 1)[1].split("\n\n", 1)[0].strip()
            return prompt

        if mode_prefix == "m":
            task_type = data[2]
            model_key = "_".join(data[3:])
            prompt = await get_current_info()
            
            if model_key not in MODELS: return
            
            ratios = MODELS[model_key]["ratios"]
            markup = types.InlineKeyboardMarkup(row_width=3)
            btns = [types.InlineKeyboardButton(r, callback_data=f"imagine_g_{task_type}_{model_key}_{r}") for r in ratios]
            markup.add(*btns)
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"imagine_back_{task_type}"))

            user = call.from_user
            username = f"@{user.username}" if user.username else user.first_name or str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"
            
            title = "𝗜𝗺𝗮𝗴𝗶𝗻𝗲" if task_type == "i" else "𝗘𝗱𝗶𝘁"
            model_name = MODELS[model_key]["name"]
            
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🖼️ <b>{title}:</b> {prompt}\n\n📐 <b>𝗦𝗲𝗹𝗲𝗰𝘁 𝗔𝘀𝗽𝗲𝗰𝘁 𝗥𝗮𝘁𝗶𝗼 ({model_name}):</b>\n{footer}",
                reply_markup=markup,
                parse_mode="HTML"
            )

        elif mode_prefix == "back":
            task_type = data[2]
            prompt = await get_current_info()
            await show_model_selection(call.message, prompt, "imagine" if task_type == "i" else "edit", edit_msg_id=call.message.message_id)

        elif mode_prefix == "g":
            task_type = data[2]
            ratio = data[-1]
            model_key = "_".join(data[3:-1])
            prompt = await get_current_info()
            
            image_url = None
            if task_type == "e":
                if call.message.reply_to_message:
                    _, image_url = await get_prompt_and_image(call.message.reply_to_message)
            
            model_info = MODELS[model_key]
            api_name = model_info["name"]
            endpoint = model_info["endpoint"]
            resp_type = model_info.get("type", "json")
            
            await bot.answer_callback_query(call.id, f"Generating {api_name}...")
            
            # Construct URL
            if model_info.get("custom"):
                 api_url = f"{endpoint}?img={quote_plus(prompt)}&ratio={ratio}"
            else:
                 api_url = f"{BASE_URL}/{endpoint}?img={quote_plus(prompt)}&ratio={ratio}"
            
            if image_url:
                api_url += f"&url={quote_plus(image_url)}"

            user = call.from_user
            username = f"@{user.username}" if user.username else user.first_name or str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🎨 <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗶𝗻𝗴 𝘄𝗶𝘁𝗵 {api_name}...</b>\n\n📝 <b>𝗣𝗿𝗼𝗺𝗽𝘁:</b> {prompt}\n📐 <b>𝗥𝗮𝘁𝗶𝗼:</b> {ratio}\n{footer}",
                parse_mode="HTML"
            )

            try:
                # Handle SSE specifically
                if resp_type == "sse":
                    import json
                    response = await asyncio.to_thread(requests.get, api_url, timeout=None, stream=True)
                    response.raise_for_status()
                    
                    final_image = None
                    last_percent = 0
                    
                    # Store message text to minimize edits
                    base_msg = f"🎨 <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗶𝗻𝗴 𝘄𝗶𝘁𝗵 {api_name}...</b>\n\n📝 <b>𝗣𝗿𝗼𝗺𝗽𝘁:</b> {prompt}\n"
                    
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            try:
                                data = json.loads(decoded_line)
                                if data.get("status") == "success":
                                    final_image = data.get("img_url")
                                    break
                                elif data.get("status") == "progress":
                                    percent = data.get("percent", 0)
                                    message_text = data.get("message", "")
                                    # Only edit every 20-30% or if message changes significantly to avoid flood limits
                                    if percent - last_percent >= 20 or percent == 100:
                                        last_percent = percent
                                        try:
                                             await bot.edit_message_text(
                                                f"{base_msg}⏳ <b>Progress:</b> {percent}%\n💬 {message_text}\n{footer}",
                                                call.message.chat.id, 
                                                call.message.message_id,
                                                parse_mode="HTML"
                                            )
                                        except Exception: 
                                            pass
                            except json.JSONDecodeError:
                                pass
                else:
                    # Normal handling
                    response = await asyncio.to_thread(requests.get, api_url, timeout=None)
                    response.raise_for_status()
                    
                    final_image = None
                    if resp_type == "bytes":
                        final_image = response.content
                    else:
                        try:
                            data_json = response.json()
                            final_image = data_json.get("url") or data_json.get("output_url")
                        except Exception:
                            pass

                if final_image:
                    caption_text = f"🖼️ <b>𝗣𝗿𝗼𝗺𝗽𝘁:</b> {prompt}\n\n✨ <b>𝗠𝗼𝗱𝗲𝗹:</b> {api_name}\n📐 <b>𝗥𝗮𝘁𝗶𝗼:</b> {ratio}\n{footer}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"
                    
                    await bot.delete_message(call.message.chat.id, call.message.message_id)
                    await bot.send_photo(
                        chat_id=call.message.chat.id,
                        photo=final_image,
                        caption=caption_text,
                        parse_mode="HTML",
                        reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None
                    )
                else:
                    await bot.edit_message_text("❌ Failed to generate. No image returned.", call.message.chat.id, call.message.message_id)
            except Exception as e:
                await bot.edit_message_text(f"❌ Error: {str(e)}", call.message.chat.id, call.message.message_id)