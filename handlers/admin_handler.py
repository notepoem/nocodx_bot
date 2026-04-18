from datetime import datetime, timedelta
import re
import asyncio

ADMIN_ID = 6785584379  # The user ID of the admin

def is_admin(user_id):
    return user_id == ADMIN_ID

def register(bot, custom_command_handler, command_prefixes_list, user_db, check_usage_limit=None):

    @custom_command_handler("fuck")
    async def handle_ban(message):
        if not is_admin(message.from_user.id):
            await bot.reply_to(message, "❌ You are not authorized to use this command.")
            return

        parts = message.text.split()
        if len(parts) < 2:
            await bot.reply_to(message, "❓ <b>𝗨𝘀𝗮𝗴𝗲:</b> <code>/fuck userid/username</code>", parse_mode="HTML")
            return

        target = parts[1]

        target_user_id = None
        all_users = user_db.get_all_users()

        if target.startswith("@"):
            username = target[1:].lower()
            for u in all_users:
                if u[1] and u[1].lower() == username:
                    target_user_id = u[0]
                    break
        else:
            try:
                target_user_id = int(target)
            except ValueError:
                pass

        if not target_user_id:
            await bot.reply_to(message, "❌ User not found.")
            return

        user_db.update_user_field(target_user_id, "is_banned", True)

        user = message.from_user
        username_footer = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
        footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username_footer}"

        await bot.reply_to(message, f"🚫 <b>𝗨𝘀𝗲𝗿 {target} has been 𝗕𝗔𝗡𝗡𝗘𝗗.</b>\n{footer}", parse_mode="HTML")

    @custom_command_handler("cumin")
    async def handle_unban(message):
        if not is_admin(message.from_user.id):
            return

        parts = message.text.split()
        if len(parts) < 2:
            return

        target = parts[1]
        target_user_id = None
        all_users = user_db.get_all_users()

        if target.startswith("@"):
            username = target[1:].lower()
            for u in all_users:
                if u[1] and u[1].lower() == username:
                    target_user_id = u[0]
                    break
        else:
            try:
                target_user_id = int(target)
            except:
                pass

        if target_user_id:
            user_db.update_user_field(target_user_id, "is_banned", False)

            user = message.from_user
            username_footer = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username_footer}"

            await bot.reply_to(message, f"✅ <b>𝗨𝘀𝗲𝗿 {target} has been 𝗨𝗡𝗕𝗔𝗡𝗡𝗘𝗗.</b>\n{footer}", parse_mode="HTML")
