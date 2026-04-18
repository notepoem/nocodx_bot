import threading
import time
import telebot.apihelper
from telebot.types import Message, InputFile
import re
import os
import asyncio

spam_threads = {}

async def _run_normal_spam_task(bot, current_chat_id, text_to_spam, current_number):
    thread = spam_threads.get(current_chat_id)
    if not thread:
        return

    message_sent_count = 0
    while not thread.stop_spam:
        try:
            if current_number is not None:
                await bot.send_message(current_chat_id, f"{text_to_spam} {current_number}")
                current_number += 1
            else:
                await bot.send_message(current_chat_id, text_to_spam)

            message_sent_count += 1
            time.sleep(0.3) # 0.3s delay between messages

        except telebot.apihelper.ApiTelegramException as e:
            print(f"Telegram API Error in spam_task for chat {current_chat_id}: {e}")
            await bot.send_message(current_chat_id, f"⚠️ Spamming stopped: A Telegram API error occurred (e.g. rate limit).\nError: `{e}`", parse_mode="Markdown")
            thread.stop_spam = True
            break
        except Exception as e:
            print(f"Generic Error in spam_task for chat {current_chat_id}: {e}")
            await bot.send_message(current_chat_id, f"⚠️ Spamming stopped: An unexpected error occurred.\nError: `{e}`", parse_mode="Markdown")
            thread.stop_spam = True
            break

    if current_chat_id in spam_threads:
        del spam_threads[current_chat_id]
    print(f"Normal spamming stopped for chat {current_chat_id}. Messages sent: {message_sent_count}")


def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None): 

    async def is_admin(chat_id, user_id):
        if chat_id > 0:  
            return True
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            return member.status in ['creator', 'administrator']
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Error checking admin status for chat {chat_id}, user {user_id}: {e}")
            return False 

    @custom_command_handler("spam")
    async def handle_spam(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "Spam"):
            return
        chat_id = message.chat.id
        user_id = message.from_user.id

        if not await is_admin(chat_id, user_id):
            await bot.reply_to(message, "⛔ This command is only for group administrators.")
            return

        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
             args = " ".join(parts_split[1:]).strip()
        else:
             args = ""

        if chat_id in spam_threads and spam_threads[chat_id].is_alive():
            spam_threads[chat_id].stop_spam = True
            await bot.reply_to(message, "✅ Spamming has been stopped.")
            return

        if not args:
            await bot.reply_to(message, f"❌ Please provide some text to spam. Example:\n`{command_prefixes_list[0]}spam Hello World`\n`{command_prefixes_list[1]}spam Number 1`", parse_mode="Markdown") 
            return

        full_text = args
        base_text = full_text
        start_number = None

        match = re.search(r'\s(\d+)$', full_text)
        if match:
            potential_number = int(match.group(1))
            if full_text.endswith(match.group(0)):
                start_number = potential_number
                base_text = full_text[:-len(match.group(0))].strip()

        spam_thread = threading.Thread(target=lambda: asyncio.run(_run_normal_spam_task(bot, chat_id, base_text, start_number)))
        spam_thread.stop_spam = False
        spam_threads[chat_id] = spam_thread
        spam_thread.daemon = True
        spam_thread.start()

        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

        await bot.reply_to(message, f"🚀 <b>𝗦𝗽𝗮𝗺𝗺𝗶𝗻𝗴 𝗦𝘁𝗮𝗿𝘁𝗲𝗱!</b>\n\nTo stop, type `{command_prefixes_list[0]}spam` or `{command_prefixes_list[1]}spam` or `{command_prefixes_list[2]}spam` again.\n{footer}", parse_mode="HTML") 

    @custom_command_handler("spmtxt")
    async def handle_spmtxt(message: Message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        parts_split = message.text.strip().split()
        if len(parts_split) > 2:
             user_input_parts = [parts_split[1], " ".join(parts_split[2:])]
        else:
             user_input_parts = []

        if len(user_input_parts) < 2 or not user_input_parts[0].isdigit():
            await bot.reply_to(message,
                         f"❌ Please use the correct format to create a text file. Example:\n"
                         f"`{command_prefixes_list[0]}spmtxt 100 Hello World`\n"
                         f"`{command_prefixes_list[1]}spmtxt 50 Number 1` (will start from 1)",
                         parse_mode="Markdown")
            return

        spam_count = int(user_input_parts[0])
        full_text_to_process = user_input_parts[1].strip() if len(user_input_parts) > 1 else ""

        if not full_text_to_process:
            await bot.reply_to(message, f"❌ Please provide some text for the file. Example: `{command_prefixes_list[0]}spmtxt 100 Hello World`", parse_mode="Markdown") 
            return

        base_text = full_text_to_process
        start_number = None

        match = re.search(r'\s(\d+)$', full_text_to_process)
        if match:
            potential_number = int(match.group(1))
            if full_text_to_process.endswith(match.group(0)):
                start_number = potential_number
                base_text = full_text_to_process[:-len(match.group(0))].strip()

        await bot.send_message(chat_id, "⏳ Generating your file, please wait...")

        generated_lines = []
        for i in range(spam_count):
            if start_number is not None:
                generated_lines.append(f"{base_text} {start_number + i}")
            else:
                generated_lines.append(base_text)

        file_content = "\n".join(generated_lines)
        cache_dir = os.path.join(os.getcwd(), "cache", "spam")
        os.makedirs(cache_dir, exist_ok=True)
        file_name = os.path.join(cache_dir, f"generated_spam_{chat_id}_{int(time.time())}.txt")

        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(file_content)

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

            with open(file_name, "rb") as f:
                await bot.send_document(chat_id, InputFile(f), caption=f"✅ <b>𝗬𝗼𝘂𝗿 𝗳𝗶𝗹𝗲 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗰𝗿𝗲𝗮𝘁𝗲𝗱!</b>\n\nYour file with `{spam_count}` lines has been generated!\n{footer}", parse_mode="HTML")

        except Exception as e:
            print(f"Error generating or sending file for chat {chat_id}: {e}")
            await bot.send_message(chat_id, f"❌ Failed to generate or send file: `{e}`", parse_mode="Markdown")
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)
                print(f"Cleaned up file: {file_name}")