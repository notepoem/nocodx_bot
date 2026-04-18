import aiohttp
import asyncio
import pycountry
import random

BIN_KEYS = [
    "PUB-0YI0cklUYMv1njw6Q597r4C7KqB",
    "PUB-0YLH18JV4B57jkQgpdNc56",
    "PUB-0YIHS5PQ235Whmj347ls0c",
    "PUB-0YB9gn5WvzZN8bQ03T8SG4"
]

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("bin")
    async def handle_bin_command(message):
        if check_usage_limit and not await check_usage_limit(message, "Bin"):
            return
        # Split command and arguments safely
        parts_split = message.text.strip().split()
        if len(parts_split) > 1:
            bin_input = " ".join(parts_split[1:]).strip()
        else:
            bin_input = ""
            await bot.reply_to(message, "❗ Please provide a BIN, example: `/bin 426633`, `.bin 426633` or `,bin 426633`", parse_mode="Markdown")
            return

        bin_number_raw = bin_input.split()[0]
        bin_number = ''.join(filter(str.isdigit, bin_number_raw))

        if not bin_number or len(bin_number) < 6:
            await bot.reply_to(message, "❌ Please provide a valid BIN (at least 6 digits).")
            return
            
        await bot.send_chat_action(message.chat.id, "typing")

        try:
            bin_info = await lookup_bin(bin_number)

            if "error" in bin_info:
                await bot.reply_to(message, f"❌ Error: {bin_info['error']}")
                return

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}\n𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿: <b>@no_coder_pro</b>"

            formatted = (
                f"💳 <b>𝗕𝗜𝗡:</b> <code>{bin_info.get('bin', 'N/A')}</code>\n"
                f"🌐 <b>𝗦𝗼𝘂𝗿𝗰𝗲:</b> <code>{bin_info.get('source', '❓ UNKNOWN')}</code>\n\n"
                f"•──────────────────────•\n"
                f"<b>𝗧𝘆𝗽𝗲:</b> <code>{bin_info.get('type', 'Error').upper()}</code> (<code>{bin_info.get('scheme', 'Error').upper()}</code>)\n"
                f"<b>𝗕𝗿𝗮𝗻𝗱:</b> <code>{bin_info.get('tier', 'Error').upper()}</code>\n"
                f"<b>𝗜𝘀𝘀𝘂𝗲𝗿:</b> <code>{bin_info.get('bank', 'Error').upper()}</code>\n"
                f"<b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆:</b> <code>{bin_info.get('country', 'Error').upper()}</code> {bin_info.get('flag', '🏳️')}\n"
                f"<b>𝗖𝘂𝗿𝗿𝗲𝗻𝗰𝘆:</b> <code>{bin_info.get('currency', 'N/A')}</code> | <b>𝗖𝗼𝗱𝗲:</b> <code>{bin_info.get('country_code', 'N/A')}</code>\n"
                f"•──────────────────────•"
                f"\n{footer}"
            )

            await bot.reply_to(message, formatted, parse_mode="HTML")

        except Exception as e:
            await bot.reply_to(message, f"❌ Internal error: {str(e)}")


async def lookup_bin(bin_number: str) -> dict:
    bin_to_use = ''.join(filter(str.isdigit, bin_number))[:6]
    headers = { "User-Agent": "Mozilla/5.0" }
    api_key = random.choice(BIN_KEYS)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://data.handyapi.com/bin/{bin_to_use}",
                headers={**headers, "x-api-key": api_key}
            ) as res:
                if res.status == 200:
                    data = await res.json()
                    if data and data.get("Status") == "SUCCESS":
                        country_code = data.get("Country", {}).get("A2", "N/A")
                        country_info = get_country_info(country_code)
                        return {
                            "bin": bin_to_use,
                            "type": data.get("Type") or "N/A",
                            "scheme": data.get("Scheme") or "N/A",
                            "tier": data.get("CardTier") or "N/A",
                            "bank": data.get("Issuer") or "N/A",
                            "country": (data.get("Country", {}).get("Name") or "N/A"),
                            "currency": country_info["currency"],
                            "country_code": country_code,
                            "flag": country_info["flag"],
                            "source": "HandyAPI (Premium)"
                        }
                else:
                    return {"error": f"API returned status {res.status}"}
    except Exception as e:
        print(f"HandyAPI error: {e}")

    return {"error": "BIN information not found."}


def get_country_info(country_code):
    info = {
        "flag": "🏳️",
        "currency": "N/A"
    }
    try:
        if country_code and country_code.upper() != "N/A":
            country = pycountry.countries.get(alpha_2=country_code.upper())
            if country:
                info["flag"] = country.flag
                try:
                    currency = pycountry.currencies.get(numeric=country.numeric)
                    info["currency"] = currency.alpha_3
                except:
                    pass
    except Exception as e:
        print(f"Pycountry lookup error for code {country_code}: {e}")
    return info