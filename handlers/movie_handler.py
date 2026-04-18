import html
import requests
from urllib.parse import urlparse
import asyncio

# API endpoint for movie search
MOVIE_API_URL = "https://movie-api-delta-flax.vercel.app/api/movie?src={query}"

async def search_movie(query):
    """Search for a movie and return download links."""
    try:
        url = MOVIE_API_URL.format(query=requests.utils.quote(query))
        response = await asyncio.to_thread(requests.get, url, timeout=60)
        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            return "❌ API Error: Something went wrong with the movie search service."

        results = data.get("results", [])
        if not results:
            return "❌ No movie found with that title."

        output_list = []
        for movie in results:
            title = movie.get("title", "N/A")
            image_url = movie.get("image_url", None)
            page_url = movie.get("page_url", "")

            movie_header = f"🎬 <b>𝗧𝗶𝘁𝗹𝗲:</b> <code>{html.escape(title)}</code>\n"
            
            if image_url:
                movie_header += f"🖼️ <b>𝗣𝗼𝘀𝘁𝗲𝗿:</b> <a href='{html.escape(image_url)}'>Click Here</a>\n"
            
            if page_url:
                movie_header += f"🔗 <b>𝗦𝗼𝘂𝗿𝗰𝗲 𝗣𝗮𝗴𝗲:</b> <a href='{html.escape(page_url)}'>Visit</a>\n"

            links_output = ""
            download_links = movie.get("download_links", [])
            if download_links:
                links_output += "📥 <b>𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗟𝗶𝗻𝗸𝘀:</b>\n"
                for link_item in download_links:
                    if "downloads" in link_item:
                        source = link_item.get("source", "Unknown")
                        link_type = link_item.get("type", "")
                        file_size = link_item.get("file_size", "")
                        
                        links_output += f"  - <b>{html.escape(source.title())}</b>"
                        if file_size:
                            links_output += f" ({html.escape(file_size)})"
                        links_output += ":\n"
                        
                        for dl in link_item.get("downloads", []):
                            quality = dl.get("quality", "Unknown")
                            dl_url = dl.get("url", "")
                            if dl_url:
                                safe_link = html.escape(dl_url)
                                links_output += f"    • {html.escape(quality)}: <a href='{safe_link}'>Click Here</a>\n"
                    else:
                        source = link_item.get("source", "Unknown")
                        link_type = link_item.get("type", "Unknown")
                        dl_url = link_item.get("url", "")
                        
                        if dl_url:
                            safe_link = html.escape(dl_url)
                            links_output += f"  - <b>{html.escape(source.title())}</b> ({html.escape(link_type)}): <a href='{safe_link}'>Click Here</a>\n"
            else:
                links_output += "🔗 No download links available."

            output_list.append(f"{movie_header}{links_output}")

        return "\n" + "\n" + "\n".join(output_list)

    except requests.exceptions.RequestException as e:
        return f"⚠️ Connection Error: Failed to connect to the movie API. Please try again later. ({str(e)})"
    except Exception as e:
        return f"⚠️ An unexpected error occurred: {str(e)}"

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit):
    @custom_command_handler("movie", "mov")
    async def handle_movie_search(message):
        if not await check_usage_limit(message, "movie"):
            return
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             movie_name = " ".join(parts_split[1:]).strip()
        else:
             movie_name = ""
        
        query = movie_name # Assign movie_name to query for consistency with existing code

        if not query:
            await bot.reply_to(message, "❌ <b>Please provide a movie title to search.</b>\nExample: <code>/mov Sultanpur</code>", parse_mode="HTML")
            return

        sent_msg = await bot.reply_to(message, "🔍 <b>Searching for movies...</b>", parse_mode="HTML")

        try:
            search_results = await search_movie(query)
            
            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

            final_text = f"<b>🔎 𝗦𝗲𝗮𝗿𝗰𝗵 𝗿𝗲𝘀𝘂𝗹𝘁𝘀 𝗳𝗼𝗿:</b> <code>{html.escape(query)}</code>\n" + search_results + "\n" + footer

            if len(final_text) > 4096:
                final_text = final_text[:4000] + "\n\n⚠️ Output trimmed..."

            await bot.edit_message_text(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                text=final_text.strip(),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception as e:
            await bot.edit_message_text(
                chat_id=sent_msg.chat.id,
                message_id=sent_msg.message_id,
                text=f"⚠️ <b>Error:</b> {str(e)}",
                parse_mode="HTML"
            )
