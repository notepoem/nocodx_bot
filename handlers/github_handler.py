import requests
import html
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import json
import time
import os
import asyncio

CACHE_DIR = os.path.join(os.getcwd(), "cache", "github")
CACHE_EXPIRY = 3600  

def split_message(text, max_length=4000):
    """Split on double-newline block boundaries to avoid cutting HTML tags."""
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""
    blocks = text.split('\n\n')

    for block in blocks:
        addition = ('\n\n' + block) if current_part else block
        if len(current_part) + len(addition) <= max_length:
            current_part += addition
        else:
            if current_part:
                parts.append(current_part)
            current_part = block

    if current_part:
        parts.append(current_part)

    return parts if parts else [text[:max_length]]

def ensure_cache_dir():
    """ক্যাশ ফোল্ডার আছে কিনা চেক করে, না থাকলে তৈরি করে"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def save_to_cache(search_id, data):
    """ক্যাশে ডেটা সেভ করা"""
    try:
        ensure_cache_dir()
        cache_file = os.path.join(CACHE_DIR, f"{search_id}.json")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Cache save error: {e}")

def load_from_cache(search_id):
    """ক্যাশ থেকে ডেটা লোড করা"""
    try:
        cache_file = os.path.join(CACHE_DIR, f"{search_id}.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Cache load error: {e}")
        return None

def clear_old_cache():
    """৫ মিনিটের পুরনো ক্যাশ ফাইল ডিলিট করা"""
    try:
        if not os.path.exists(CACHE_DIR):
            return
        
        current_time = time.time()
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(CACHE_DIR, filename)
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > CACHE_EXPIRY:
                    os.remove(filepath)
                    print(f"Deleted expired cache: {filename}")
    except Exception as e:
        print(f"Cache cleanup error: {e}")

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    def create_github_keyboard(search_query, current_page, total_pages, search_id):
        """ইনলাইন কিবোর্ড তৈরি করার ফাংশন"""
        keyboard = InlineKeyboardMarkup(row_width=3)
        buttons = []

        if current_page > 1:
            buttons.append(InlineKeyboardButton(
                "⬅️ Previous", 
                callback_data=f"github_{search_id}_{current_page-1}"
            ))

        buttons.append(InlineKeyboardButton(
            f"📄 {current_page}/{total_pages}", 
            callback_data="github_page_info"
        ))

        if current_page < total_pages:
            buttons.append(InlineKeyboardButton(
                "Next ➡️", 
                callback_data=f"github_{search_id}_{current_page+1}"
            ))

        keyboard.add(*buttons)

        keyboard.add(InlineKeyboardButton(
            "🔄 New Search", 
            callback_data="github_new_search"
        ))

        return keyboard

    async def get_github_results(search_query, search_id):
        """GitHub থেকে রেজাল্ট নেওয়া বা ক্যাশ থেকে পড়া"""
        clear_old_cache()
        
        cached_data = load_from_cache(search_id)
        if cached_data:
            return cached_data['results']

        try:
            api_url = f"https://github-src.vercel.app/search?query={search_query}"

            response = await asyncio.to_thread(requests.get, api_url, timeout=60)

            if response.status_code == 200:
                results = response.json()
                cache_data = {
                    'results': results,
                    'query': search_query,
                    'timestamp': time.time(),
                    'message_ids': []
                }
                save_to_cache(search_id, cache_data)
                return results
            else:
                return None

        except requests.exceptions.RequestException as e:
            print(f"GitHub API request error: {e}")
            return None
        except Exception as e:
            print(f"GitHub API general error: {e}")
            return None

    def format_github_message(results, search_query, page_number, user, results_per_page=5):
        """গিটহাব মেসেজ ফরম্যাট করা"""
        if not results:
            return "❌ কোন রেজাল্ট পাওয়া যায়নি।"

        total_pages = (len(results) + results_per_page - 1) // results_per_page
        page_number = max(1, min(page_number, total_pages))

        start_index = (page_number - 1) * results_per_page
        end_index = start_index + results_per_page
        page_results = results[start_index:end_index]

        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

        message_parts = []
        message_parts.append(f"🔍 <b>𝗚𝗶𝘁𝗛𝘂𝗯 𝗦𝗲𝗮𝗿𝗰𝗵 𝗥𝗲𝘀𝘂𝗹𝘁𝘀:</b> <code>{html.escape(search_query)}</code>\n")
        message_parts.append(f"📄 <b>𝗣𝗮𝗴𝗲 {page_number} 𝗼𝗳 {total_pages}</b> • <b>𝗧𝗼𝘁𝗮𝗹: {len(results)} 𝗿𝗲𝗽𝗼𝘀</b>\n")

        for i, repo in enumerate(page_results, start_index + 1):
            title = repo.get('title', 'No title')
            url = repo.get('url', '')
            description = repo.get('description', 'No description available')

            description = description.replace('\n', ' ').strip()
            if len(description) > 120:
                description = description[:120] + "..."

            repo_name = title.replace('GitHub - ', '').split(':')[0]
            if len(repo_name) > 50:
                repo_name = repo_name[:50] + "..."

            repo_info = f"<b>{i}. <a href=\"{html.escape(url, quote=True)}\">{html.escape(repo_name)}</a></b>\n"
            repo_info += f"<code>{html.escape(description)}</code>\n"

            message_parts.append(repo_info)

        return "\n".join(message_parts) + "\n" + footer, total_pages

    @custom_command_handler("github")
    async def github_search_handler(message: Message):
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             search_query = " ".join(parts_split[1:]).strip()
        else:
             search_query = ""

        if not search_query:
            await bot.reply_to(message, f"❌ Usage: `{command_prefixes_list[0]}github <search query>`\n"
                                  f"📚 Example:\n"
                                  f"`{command_prefixes_list[0]}github flask react`\n"
                                  f"`{command_prefixes_list[0]}github python bot`\n"
                                  f"`{command_prefixes_list[0]}github machine learning`",
                                  parse_mode="Markdown")
            return

        search_id = f"{message.chat.id}_{message.id}"

        sent_message = await bot.reply_to(message, "⏳ Fetching information from GitHub, please wait...")

        async def fetch_and_edit_message():
            try:
                results = await get_github_results(search_query, search_id)

                if results is None:
                    await bot.edit_message_text(
                        chat_id=sent_message.chat.id,
                        message_id=sent_message.message_id,
                        text="❌ There was a problem searching GitHub. Please try again later."
                    )
                    return

                if not results:
                    await bot.edit_message_text(
                        chat_id=sent_message.chat.id,
                        message_id=sent_message.message_id,
                        text=f"❌ No repositories found for '{search_query}'."
                    )
                    return

                message_text, total_pages = format_github_message(results, search_query, 1, message.from_user)
                message_parts = split_message(message_text)
                keyboard = create_github_keyboard(search_query, 1, total_pages, search_id)
                message_ids = [sent_message.message_id]

                await bot.edit_message_text(
                    chat_id=sent_message.chat.id,
                    message_id=sent_message.message_id,
                    text=message_parts[0],
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=keyboard if len(message_parts) == 1 else None
                )

                for i, part in enumerate(message_parts[1:], start=2):
                    is_last = i == len(message_parts)
                    sent = await bot.send_message(
                        chat_id=sent_message.chat.id,
                        text=part,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=keyboard if is_last else None
                    )
                    message_ids.append(sent.message_id)

                cached_data = load_from_cache(search_id)
                if cached_data:
                    cached_data['message_ids'] = message_ids
                    cached_data['chat_id'] = sent_message.chat.id
                    save_to_cache(search_id, cached_data)

            except Exception as e:
                print(f"Thread operation error: {e}")
                try:
                    await bot.edit_message_text(
                        chat_id=sent_message.chat.id,
                        message_id=sent_message.message_id,
                        text=f"❌ একটি ত্রুটি ঘটেছে: {str(e)}"
                    )
                except:
                    pass

        await fetch_and_edit_message()

    @bot.callback_query_handler(func=lambda call: call.data.startswith('github_'))
    async def handle_github_callback(call):
        if check_usage_limit and not await check_usage_limit(call.message, "Github"):
            return
        try:
            data_parts = call.data.split('_')

            if call.data == "github_new_search":
                await bot.answer_callback_query(call.id, "🔄 নতুন সার্চ করতে /github কমান্ড ব্যবহার করুন")
                return

            if call.data == "github_page_info":
                await bot.answer_callback_query(call.id, "📄 বর্তমান পেজের তথ্য")
                return

            if len(data_parts) >= 4:
                search_id = f"{data_parts[1]}_{data_parts[2]}"
                page_number = int(data_parts[3])

                cache_data = load_from_cache(search_id)
                
                if cache_data:
                    results = cache_data['results']
                    search_query = cache_data['query']
                    old_message_ids = cache_data.get('message_ids', [])
                    chat_id = cache_data.get('chat_id', call.message.chat.id)

                    for msg_id in old_message_ids[1:]:
                        try:
                            await bot.delete_message(chat_id, msg_id)
                        except:
                            pass

                    message_text, total_pages = format_github_message(results, search_query, page_number, call.from_user)
                    message_parts = split_message(message_text)
                    keyboard = create_github_keyboard(search_query, page_number, total_pages, search_id)
                    new_message_ids = [old_message_ids[0] if old_message_ids else call.message.message_id]

                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=new_message_ids[0],
                        text=message_parts[0],
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                        reply_markup=keyboard if len(message_parts) == 1 else None
                    )

                    for i, part in enumerate(message_parts[1:], start=2):
                        is_last = i == len(message_parts)
                        sent = await bot.send_message(
                            chat_id=chat_id,
                            text=part,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                            reply_markup=keyboard if is_last else None
                        )
                        new_message_ids.append(sent.message_id)

                    cache_data['message_ids'] = new_message_ids
                    save_to_cache(search_id, cache_data)

                    await bot.answer_callback_query(call.id, f"📄 পেজ {page_number}")
                else:
                    await bot.answer_callback_query(call.id, "❌ সেশন এক্সপায়ার্ড, নতুন করে সার্চ করুন")

        except Exception as e:
            print(f"Callback error: {e}")
            await bot.answer_callback_query(call.id, "❌ ত্রুটি ঘটেছে")