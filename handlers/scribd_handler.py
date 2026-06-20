import requests
import os
import html
from urllib.parse import quote
import asyncio

async def download_pdf(url, filepath):
    """Download PDF from URL and save to local cache"""
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=120, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"PDF download error: {e}")
        return False

async def get_scribd_info(url):
    """Fetch Scribd document info from the new API"""
    api_url = f"https://scribd-dl-cookies.vercel.app/api/scribd?url={quote(url)}"
    try:
        response = await asyncio.to_thread(requests.get, api_url, timeout=60)
        response.raise_for_status()
        data = response.json()

        if data.get('title'):
            return {
                'success': True,
                'title': data.get('title', 'N/A'),
                'author': data.get('author_name', 'N/A'),
                'pdf_url': data.get('download_link', ''),
                'source_url': data.get('main_url', url)
            }
        else:
            return {'success': False, 'error': 'Failed to extract document info.'}
    except Exception as e:
        return {'success': False, 'error': f"API Error: {str(e)}"}

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("scribd")
    async def handle_scribd(message):
        if check_usage_limit and not await check_usage_limit(message, "Scribd"):
            return
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             url = " ".join(parts_split[1:]).strip()
        else:
             url = ""

        if not url:
            await bot.reply_to(message, 
                f"❌ URL Missing!\n\n"
                f"Usage: `{command_prefixes_list[0]}scribd <Scribd URL>`\n"
                f"Example: `{command_prefixes_list[0]}scribd https://www.scribd.com/document/12345/Title`",
                parse_mode="Markdown")
            return

        if 'scribd.com' not in url:
            await bot.reply_to(message, "❌ Invalid URL! Please provide a valid Scribd document link.")
            return

        sent_msg = await bot.reply_to(message, "⏳ Fetching document information...")

        result = await get_scribd_info(url)

        if not result['success']:
            await bot.edit_message_text(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                text=f"❌ Error: {result['error']}"
            )
            return

        info_text = (
            f"📄 <b>𝗦𝗰𝗿𝗶𝗯𝗱 𝗗𝗼𝗰𝘂𝗺𝗲𝗻𝘁 𝗙𝗼𝘂𝗻𝗱</b>\n\n"
            f"📌 <b>𝗧𝗶𝘁𝗹𝗲:</b> {html.escape(result['title'])}\n"
            f"✍️ <b>𝗔𝘂𝘁𝗵𝗼𝗿:</b> {html.escape(result['author'])}\n"
        )

        if not result['pdf_url']:
            await bot.edit_message_text(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                text=info_text + "\n❌ Download link not available for this document.",
                parse_mode="HTML"
            )
            return

        filename = f"scribd_{message.chat.id}_{message.message_id}.pdf"
        cache_dir = os.path.join(os.getcwd(), "cache", "scribd")
        filepath = os.path.join(cache_dir, filename)
        os.makedirs(cache_dir, exist_ok=True)

        await bot.edit_message_text(
            chat_id=sent_msg.chat.id,
            message_id=sent_msg.message_id,
            text="⏳ Downloading PDF to server..."
        )

        try:
            if await download_pdf(result['pdf_url'], filepath):
                file_size = os.path.getsize(filepath)
                size_mb = file_size / (1024 * 1024)

                user = message.from_user
                username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
                footer = f"\n\n•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

                final_caption = info_text + f"📦 <b>𝗦𝗶𝘇𝗲:</b> {size_mb:.2f} MB\n"
                final_caption += f"🔗 <b>𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗟𝗶𝗻𝗸:</b> <a href='{html.escape(result['pdf_url'])}'>𝗖𝗹𝗶𝗰𝗸 𝗛𝗲𝗿𝗲</a>\n"
                final_caption += f"🌐 <b>𝗦𝗼𝘂𝗿𝗰𝗲:</b> <a href='{html.escape(result['source_url'])}'>𝗦𝗰𝗿𝗶𝗯𝗱 𝗣𝗮𝗴𝗲</a>"
                final_caption += footer

                if file_size > 50 * 1024 * 1024:
                    await bot.edit_message_text(
                        chat_id=sent_msg.chat.id,
                        message_id=sent_msg.message_id,
                        text=final_caption + "\n\n⚠️ <i>File is larger than 50MB. Please use the link above.</i>",
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                else:
                    with open(filepath, 'rb') as doc:
                        await bot.send_document(
                            message.chat.id,
                            doc,
                            caption=final_caption,
                            parse_mode="HTML",
                            reply_to_message_id=message.message_id
                        )
                    await bot.delete_message(sent_msg.chat.id, sent_msg.message_id)
            else:
                raise Exception("Server failed to capture PDF.")

        except Exception as e:
            error_text = info_text + f"\n❌ <b>Failed to send file:</b> {html.escape(str(e))}\n"
            error_text += f"🔗 <b>Download Link:</b> <a href='{html.escape(result['pdf_url'])}'>Click Here</a>"
            await bot.edit_message_text(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                text=error_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
