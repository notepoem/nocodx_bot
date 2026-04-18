import requests
import html
from urllib.parse import quote_plus
import asyncio

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("terabox", "tbox")
    async def handle_terabox(message):
        if check_usage_limit and not await check_usage_limit(message, "Terabox"):
            return
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             url = " ".join(parts_split[1:]).strip()
        else:
             url = ""

        if not url:
            await bot.reply_to(message, f"❌ Terabox URL missing! Usage: `{command_prefixes_list[0]}terabox <url>`", parse_mode="Markdown")
            return

        processing_msg = await bot.reply_to(message, "🔎 Fetching Terabox download links...")

        try:
            api_url = f"https://teraplay.bbinl.site/api/download?url={quote_plus(url)}"
            response = await asyncio.to_thread(requests.get, api_url, timeout=60)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success" and data.get("Extracted Info"):
                extracted_info = data["Extracted Info"]
                
                if len(extracted_info) == 1:
                    info = extracted_info[0]
                    title = info.get("Title", "N/A")
                    size = info.get("Size", "Unknown")
                    download_link = info.get("Direct Download Link", "")
                    streaming_url = info.get("streaming_url", "")
                    
                    thumbnails = info.get("Thumbnails", {})
                    thumb_highest = None
                    if "850x580" in thumbnails:
                        thumb_highest = thumbnails["850x580"]
                    elif "360x270" in thumbnails:
                        thumb_highest = thumbnails["360x270"]
                    elif "140x90" in thumbnails:
                        thumb_highest = thumbnails["140x90"]
                    elif thumbnails:
                        thumb_highest = list(thumbnails.values())[0]

                    user = message.from_user
                    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                    footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                    caption = (
                        f"📦 <b>𝗧𝗲𝗿𝗮𝗯𝗼𝘅 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱</b>\n\n"
                        f"📄 <b>𝗙𝗶𝗹𝗲:</b> {html.escape(title)}\n"
                        f"💾 <b>𝗦𝗶𝘇𝗲:</b> {size}\n\n"
                        f"🔗 <a href='{download_link}'>𝗗𝗶𝗿𝗲𝗰𝘁 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗟𝗶𝗻𝗸</a>\n"
                        f"📺 <a href='{streaming_url}'>𝗦𝘁𝗿𝗲𝗮𝗺𝗶𝗻𝗴 𝗨𝗥𝗟</a>"
                        f"\n{footer}"
                    )

                    if thumb_highest:
                        try:
                            await bot.send_photo(
                                message.chat.id,
                                thumb_highest,
                                caption=caption,
                                parse_mode="HTML",
                                reply_to_message_id=message.message_id
                            )
                            await bot.delete_message(message.chat.id, processing_msg.message_id)
                        except:
                            await bot.edit_message_text(
                                chat_id=message.chat.id,
                                message_id=processing_msg.message_id,
                                text=caption,
                                parse_mode="HTML",
                                disable_web_page_preview=True
                            )
                    else:
                        await bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=processing_msg.message_id,
                            text=caption,
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                else:
                    user = message.from_user
                    username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                    footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

                    # Multiple files found
                    msg_text = (
                        f"📂 <b>𝗠𝘂𝗹𝘁𝗶𝗽𝗹𝗲 𝗙𝗶𝗹𝗲𝘀 𝗗𝗲𝘁𝗲𝗰𝘁𝗲𝗱 ({len(extracted_info)})</b>\n\n"
                        f"Please use our website for a better experience:\n"
                        f"🌐 <a href='https://teraplay.bbinl.site/'>teraplay.bbinl.site</a>"
                        f"\n{footer}"
                    )
                    await bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=processing_msg.message_id,
                        text=msg_text,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
            else:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=processing_msg.message_id,
                    text="❌ Failed to get data from Terabox. Please check the URL and try again."
                )

        except Exception as e:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=processing_msg.message_id,
                text=f"❌ Error: {str(e)}"
            )
