import os
import re
import requests
import pytz
import pycountry
from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from telebot.apihelper import ApiTelegramException
import asyncio

executor = ThreadPoolExecutor(max_workers=4)
weather_cache = {}
CACHE_DURATION = timedelta(minutes=10)

def get_timezone_from_coordinates(lat, lon):
    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        if timezone_str:
            return pytz.timezone(timezone_str)
    except Exception:
        pass
    timezone_mapping = {
        'BD': 'Asia/Dhaka', 'IN': 'Asia/Kolkata', 'PK': 'Asia/Karachi',
        'US': 'America/New_York', 'GB': 'Europe/London', 'FR': 'Europe/Paris',
        'DE': 'Europe/Berlin', 'JP': 'Asia/Tokyo', 'CN': 'Asia/Shanghai',
        'AU': 'Australia/Sydney', 'CA': 'America/Toronto', 'BR': 'America/Sao_Paulo',
        'RU': 'Europe/Moscow', 'AE': 'Asia/Dubai', 'SA': 'Asia/Riyadh'
    }
    return pytz.timezone(timezone_mapping.get('BD', 'UTC'))

def get_country_name(country_code):
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else country_code
    except Exception:
        return country_code

def create_weather_image(weather_data, output_path):
    # Ensure cache directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img_width, img_height = 1000, 600  
    background_color = (25, 35, 45)
    img = Image.new("RGB", (img_width, img_height), color=background_color)
    draw = ImageDraw.Draw(img)

    try:
        timezone = get_timezone_from_coordinates(weather_data["lat"], weather_data["lon"])
        local_time = datetime.now(timezone)
        time_text = local_time.strftime("%I:%M %p")
        date_text = local_time.strftime("%A, %d %B")
    except Exception:
        time_text = datetime.now().strftime("%I:%M %p")
        date_text = datetime.now().strftime("%A, %d %B")

    current = weather_data["current"]
    temp_text = f"{current['temp']}°C"
    condition_text = current["weather"]
    realfeel_text = f"Real Feel {current['feels_like']}°C"
    country_name = get_country_name(weather_data['country_code'])
    location_text = f"{weather_data['city']}, {country_name}"

    white = (255, 255, 255)
    light_blue = (100, 200, 255)
    yellow = (255, 255, 100)
    light_gray = (180, 180, 180)
    orange = (255, 200, 50)

    DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        _f = DEJAVU_BOLD if os.path.exists(DEJAVU_BOLD) else DEJAVU if os.path.exists(DEJAVU) else None
        _fr = DEJAVU if os.path.exists(DEJAVU) else None
        font_xlarge = ImageFont.truetype(_f, 80) if _f else ImageFont.load_default().font_variant(size=80)
        font_large  = ImageFont.truetype(_f, 50) if _f else ImageFont.load_default().font_variant(size=50)
        font_medium = ImageFont.truetype(_f, 35) if _f else ImageFont.load_default().font_variant(size=35)
        font_small  = ImageFont.truetype(_fr, 28) if _fr else ImageFont.load_default().font_variant(size=28)
    except Exception:
        font_xlarge = ImageFont.load_default().font_variant(size=80)
        font_large  = ImageFont.load_default().font_variant(size=50)
        font_medium = ImageFont.load_default().font_variant(size=35)
        font_small  = ImageFont.load_default().font_variant(size=28)

    draw.text((50, 20), location_text, font=font_medium, fill=light_blue)
    draw.text((50, 60), date_text, font=font_small, fill=light_gray)
    time_bbox = draw.textbbox((0, 0), time_text, font=font_medium)
    time_width = time_bbox[2] - time_bbox[0]
    draw.text((img_width - 50 - time_width, 30), time_text, font=font_medium, fill=yellow)
    draw.text((50, 120), temp_text, font=font_xlarge, fill=white)
    draw.text((50, 220), condition_text, font=font_large, fill=light_blue)
    draw.text((50, 280), realfeel_text, font=font_medium, fill=light_gray)

    details_left = [
        f"• Humidity: {current['humidity']}%",
        f"• Wind: {current['wind_speed']} m/s",
        f"• Direction: {current['wind_dir']}\u00b0"
    ]

    details_right = [
        f"• Sunrise: {current['sunrise']}",
        f"• Sunset: {current['sunset']}",
        f"• Updated: {current['time']}"
    ]

    for i, detail in enumerate(details_left):
        y_pos = 350 + (i * 45)
        draw.text((50, y_pos), detail, font=font_small, fill=white)

    for i, detail in enumerate(details_right):
        y_pos = 350 + (i * 45)
        draw.text((img_width//2 + 50, y_pos), detail, font=font_small, fill=white)

    footer_text = f"Weather data for {weather_data['city']}"
    draw.text((50, img_height - 40), footer_text, font=font_small, fill=light_gray)

    img.save(output_path)
    return output_path

async def get_weather_data(city):
    cache_key = city.lower()
    current_time = datetime.now()

    if cache_key in weather_cache:
        cached_data, timestamp = weather_cache[cache_key]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        if current_time - timestamp < CACHE_DURATION:
            return cached_data

    try:
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geocode_response = await asyncio.to_thread(requests.get, geocode_url)
        geocode_response.raise_for_status()
        geocode_data = geocode_response.json()

        if not geocode_data or "results" not in geocode_data or not geocode_data["results"]:
            return None

        result = geocode_data["results"][0]
        lat, lon = result["latitude"], result["longitude"]
        country_code = result.get("country_code", "").upper()

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,apparent_temperature,weathercode,"
            f"wind_speed_10m,wind_direction_10m&"
            f"hourly=temperature_2m,apparent_temperature,relative_humidity_2m,weathercode,"
            f"precipitation_probability&"
            f"daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,weathercode&"
            f"timezone=auto"
        )

        aqi_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality?"
            f"latitude={lat}&longitude={lon}&"
            f"hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone&"
            f"timezone=auto"
        )

        weather_response = await asyncio.to_thread(requests.get, weather_url)
        aqi_response = await asyncio.to_thread(requests.get, aqi_url)
        weather_response.raise_for_status()
        aqi_response.raise_for_status()

        weather_data = weather_response.json()
        aqi_data = aqi_response.json()

        if not weather_data or not aqi_data:
            return None

        current = weather_data["current"]
        hourly = weather_data["hourly"]
        daily = weather_data["daily"]
        aqi = aqi_data["hourly"]

        weather_code = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Fog", 48: "Rime Fog", 51: "Light Drizzle", 53: "Moderate Drizzle",
            55: "Dense Drizzle", 61: "Light Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            66: "Freezing Rain", 67: "Heavy Freezing Rain", 71: "Light Snow",
            73: "Moderate Snow", 75: "Heavy Snow", 77: "Snow Grains", 80: "Rain Showers",
            81: "Heavy Showers", 82: "Violent Showers", 85: "Snow Showers",
            86: "Heavy Snow Showers", 95: "Thunderstorm", 96: "Thunderstorm with Hail",
            99: "Heavy Thunderstorm"
        }

        current_weather = weather_code.get(current["weathercode"], "Unknown")

        hourly_data = []
        for i in range(min(12, len(hourly["time"]))):
            time_str = hourly["time"][i].split("T")[1][:5]
            temp = hourly["temperature_2m"][i]
            code = hourly["weathercode"][i]
            weather_desc = weather_code.get(code, "Unknown")
            hour = int(time_str[:2])
            time_format = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            hourly_data.append(f"{time_format}: {temp}°C {weather_desc}")

        current_date = datetime.now()
        daily_strings = []
        for i in range(min(7, len(daily["time"]))):
            day_date = (current_date + timedelta(days=i)).strftime('%a, %b %d')
            min_temp = daily["temperature_2m_min"][i]
            max_temp = daily["temperature_2m_max"][i]
            weather = weather_code.get(daily["weathercode"][i], "Unknown")
            daily_strings.append(f"{day_date}: {min_temp} / {max_temp}°C {weather}")

        pm25_value = aqi["pm2_5"][0] if aqi["pm2_5"] else 0
        aqi_level = "Good" if pm25_value <= 12 else "Moderate" if pm25_value <= 35 else "Fair" if pm25_value <= 55 else "Poor"

        try:
            timezone = get_timezone_from_coordinates(lat, lon)
            local_time = datetime.now(timezone)
            current_time_str = local_time.strftime("%I:%M %p")
        except Exception:
            current_time_str = datetime.now().strftime("%I:%M %p")

        result_data = {
            "current": {
                "temp": round(current["temperature_2m"], 1),
                "feels_like": round(current["apparent_temperature"], 1),
                "humidity": current["relative_humidity_2m"],
                "wind_speed": current["wind_speed_10m"],
                "wind_dir": current["wind_direction_10m"],
                "weather": current_weather,
                "sunrise": daily["sunrise"][0].split("T")[1][:5] if daily["sunrise"] else "06:00",
                "sunset": daily["sunset"][0].split("T")[1][:5] if daily["sunset"] else "18:00",
                "time": current_time_str
            },
            "hourly": hourly_data,
            "daily": daily_strings,
            "aqi": {
                "pm25": round(pm25_value, 1),
                "pm10": round(aqi["pm10"][0], 1) if aqi["pm10"] else 0,
                "co": round(aqi["carbon_monoxide"][0], 1) if aqi["carbon_monoxide"] else 0,
                "no2": round(aqi["nitrogen_dioxide"][0], 1) if aqi["nitrogen_dioxide"] else 0,
                "o3": round(aqi["ozone"][0], 1) if aqi["ozone"] else 0,
                "level": aqi_level
            },
            "city": city.capitalize(),
            "country": get_country_name(country_code),
            "country_code": country_code,
            "lat": lat,
            "lon": lon
        }

        weather_cache[cache_key] = (result_data, datetime.now())
        return result_data

    except Exception as e:
        print(f"Error fetching weather data for {city}: {e}")
        return None

def register(bot: TeleBot, custom_command_handler, command_prefixes_list, check_usage_limit=None):
    @custom_command_handler("wth")
    async def handle_weather(message: Message):
        if check_usage_limit and not await check_usage_limit(message, "weather"):
            return
        parts = message.text.split()
        if len(parts) < 2:
            await bot.reply_to(message, "**Please provide a city name. Example: `/wth Faridpur`**", parse_mode="Markdown")
            return

        city = parts[1].lower()
        loading_msg = await bot.reply_to(message, "**Processing weather data...**", parse_mode="Markdown")

        try:
            data = await get_weather_data(city)
            if not data:
                await bot.edit_message_text(
                    f"🔍 Weather data not found for `{city.capitalize()}`. Please check the city name and try again.", 
                    message.chat.id, 
                    loading_msg.message_id, 
                    parse_mode="HTML"
                )
                return

            cache_dir = os.path.join(os.getcwd(), "cache", "wth")
            image_path = os.path.join(cache_dir, f"weather_{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            executor.submit(create_weather_image, data, image_path).result()

            user = message.from_user
            if user.username:
                user_fullname = f"@{user.username}"
            elif user.first_name:
                user_fullname = f"{user.first_name} {user.last_name or ''}".strip()
            else:
                user_fullname = str(user.id)
            keyboard = [
                [InlineKeyboardButton("🕒 12-Hour Forecast", callback_data=f"12h_{message.from_user.id}_{city}"), 
                 InlineKeyboardButton("📅 7-Day Forecast", callback_data=f"7d_{message.from_user.id}_{city}")],
                [InlineKeyboardButton("🌬 Air Quality", callback_data=f"aqi_{message.from_user.id}_{city}"), 
                 InlineKeyboardButton("⚠️ Alerts", callback_data=f"alert_{message.from_user.id}_{city}")],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{message.from_user.id}_{city}"), 
                 InlineKeyboardButton("🗺 Map & Radar", callback_data=f"map_{message.from_user.id}_{city}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            user = message.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            caption = (
                f"🔍 <b>𝗪𝗲𝗮𝘁𝗵𝗲𝗿 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"🌍 <b>𝗟𝗼𝗰𝗮𝘁𝗶𝗼𝗻:</b> {data['city']}, {data['country']}\n"
                f"🕒 <b>𝗧𝗶𝗺𝗲:</b> {data['current']['time']}\n"
                f"🌡 <b>𝗧𝗲𝗺𝗽:</b> {data['current']['temp']}°C\n"
                f"🌡 <b>𝗙𝗲𝗲𝗹𝘀 𝗟𝗶𝗸𝗲:</b> {data['current']['feels_like']}°C\n"
                f"💧 <b>𝗛𝘂𝗺𝗶𝗱𝗶𝘁𝘆:</b> {data['current']['humidity']}%\n"
                f"🌬 <b>𝗪𝗶𝗻𝗱:</b> {data['current']['wind_speed']} m/s from {data['current']['wind_dir']}°\n"
                f"🌅 <b>𝗦𝘂𝗻𝗿𝗶𝘀𝗲:</b> {data['current']['sunrise']}\n"
                f"🌇 <b>𝗦𝘂𝗻𝘀𝗲𝘁:</b> {data['current']['sunset']}\n"
                f"🌤 <b>𝗖𝗼𝗻𝗱𝗶𝘁𝗶𝗼𝗻:</b> {data['current']['weather']}\n"
                f"\n{footer}"
            )

            with open(image_path, "rb") as image_file:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=image_file,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            os.remove(image_path)
            await bot.delete_message(message.chat.id, loading_msg.message_id)

        except Exception as e:
            await bot.edit_message_text(
                f"❌ Error downloading/processing:\n`{str(e)}`", 
                message.chat.id, 
                loading_msg.message_id, 
                parse_mode="HTML"
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('12h_', '7d_', 'aqi_', 'alert_', 'map_', 'refresh_', 'wth_menu_')))
    async def callback_button(call: CallbackQuery):
        match = re.match(r"^(12h|7d|aqi|alert|map|refresh|wth_menu)_(\d+)_(.+)$", call.data)
        if not match:
            await bot.answer_callback_query(call.id, "Error: Invalid button data.", show_alert=True)
            return

        action, original_user_id, city = match.groups()
        original_user_id = int(original_user_id)
        callback_user_id = call.from_user.id

        if callback_user_id != original_user_id:
            try:
                await bot.answer_callback_query(
                    call.id,
                    f"Only the requester can use this button.",
                    show_alert=True
                )
            except:
                await bot.answer_callback_query(
                    call.id,
                    "Only the requester can use this button.",
                    show_alert=True
                )
            return

        await bot.answer_callback_query(call.id, "Loading...")

        if action == "refresh":
            cache_key = city.lower()
            if cache_key in weather_cache:
                del weather_cache[cache_key]

        data = await get_weather_data(city)
        if not data:
            try:
                await bot.edit_message_caption(
                    f"🔍 Weather data not found for `{city.capitalize()}`. Please try again.", 
                    call.message.chat.id, 
                    call.message.message_id, 
                    parse_mode="HTML"
                )
            except ApiTelegramException:
                await bot.send_message(
                    call.message.chat.id, 
                    f"🔍 Weather data not found for `{city.capitalize()}`. Please try again.", 
                    parse_mode="HTML"
                )
            return

        user = call.from_user
        if user.username:
            user_fullname = f"@{user.username}"
        elif user.first_name:
            user_fullname = f"{user.first_name} {user.last_name or ''}".strip()
        else:
            user_fullname = str(user.id)
        keyboard_back = [[InlineKeyboardButton("🔙 Back", callback_data=f"wth_menu_{original_user_id}_{city}")]]
        keyboard_main = [
            [InlineKeyboardButton("🕒 12-Hour Forecast", callback_data=f"12h_{original_user_id}_{city}"), 
             InlineKeyboardButton("📅 7-Day Forecast", callback_data=f"7d_{original_user_id}_{city}")],
            [InlineKeyboardButton("🌬 Air Quality", callback_data=f"aqi_{original_user_id}_{city}"), 
             InlineKeyboardButton("⚠️ Alerts", callback_data=f"alert_{original_user_id}_{city}")],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{original_user_id}_{city}"), 
             InlineKeyboardButton("🗺 Map & Radar", callback_data=f"map_{original_user_id}_{city}")]
        ]
        reply_markup_main = InlineKeyboardMarkup(keyboard_main)

        if action == "12h":
            hourly_text = "\n".join(data['hourly'])
            message_text = (
                f"🕒 <b>𝟭𝟮-𝗛𝗼𝘂𝗿 𝗙𝗼𝗿𝗲𝗰𝗮𝘀𝘁 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"{hourly_text}"
            )
            try:
                await bot.edit_message_caption(
                    message_text, 
                    call.message.chat.id, 
                    call.message.message_id, 
                    reply_markup=InlineKeyboardMarkup(keyboard_back), 
                    parse_mode="HTML"
                )
            except ApiTelegramException:
                pass

        elif action == "7d":
            daily_text = "\n".join(data['daily'])
            message_text = (
                f"📅 <b>𝟳-𝗗𝗮𝘆 𝗙𝗼𝗿𝗲𝗰𝗮𝘀𝘁 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"{daily_text}"
            )
            try:
                await bot.edit_message_caption(
                    message_text, 
                    call.message.chat.id, 
                    call.message.message_id, 
                    reply_markup=InlineKeyboardMarkup(keyboard_back), 
                    parse_mode="HTML"
                )
            except ApiTelegramException:
                pass

        elif action == "aqi":
            aqi = data["aqi"]
            message_text = (
                f"🌬 <b>𝗔𝗶𝗿 𝗤𝘂𝗮𝗹𝗶𝘁𝘆 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"<b>𝗢𝘃𝗲𝗿𝗮𝗹𝗹 𝗔𝗤𝗜:</b> {aqi['level']} 🟡\n"
                f"<b>𝗖𝗢:</b> {aqi['co']} µg/m³\n"
                f"<b>𝗡𝗢𝟮:</b> {aqi['no2']} µg/m³\n"
                f"<b>𝗢𝟯:</b> {aqi['o3']} µg/m³\n"
                f"<b>𝗣𝗠𝟮.𝟱:</b> {aqi['pm25']} µg/m³\n"
                f"<b>𝗣𝗠𝟭𝟬:</b> {aqi['pm10']} µg/m³"
            )
            try:
                await bot.edit_message_caption(
                    message_text, 
                    call.message.chat.id, 
                    call.message.message_id, 
                    reply_markup=InlineKeyboardMarkup(keyboard_back), 
                    parse_mode="HTML"
                )
            except ApiTelegramException:
                pass

        elif action == "alert":
            message_text = (
                f"🛡 <b>𝗪𝗲𝗮𝘁𝗵𝗲𝗿 𝗔𝗹𝗲𝗿𝘁𝘀 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"✅ No active weather alerts at the moment."
            )
            try:
                await bot.edit_message_caption(
                    message_text, 
                    call.message.chat.id, 
                    call.message.message_id, 
                    reply_markup=InlineKeyboardMarkup(keyboard_back), 
                    parse_mode="HTML"
                )
            except ApiTelegramException:
                pass

        elif action == "map":
            lat, lon = data["lat"], data["lon"]
            map_links = [
                f"[🌡 Temperature](https://openweathermap.org/weathermap?basemap=map&cities=true&layer=temperature&lat={lat}&lon={lon}&zoom=8)",
                f"[☁️ Cloud Cover](https://openweathermap.org/weathermap?basemap=map&cities=true&layer=clouds&lat={lat}&lon={lon}&zoom=8)",
                f"[🌧 Precipitation](https://openweathermap.org/weathermap?basemap=map&cities=true&layer=precipitation&lat={lat}&lon={lon}&zoom=8)",
                f"[💨 Wind Speed](https://openweathermap.org/weathermap?basemap=map&cities=true&layer=wind&lat={lat}&lon={lon}&zoom=8)",
                f"[🌊 Pressure](https://openweathermap.org/weathermap?basemap=map&cities=true&layer=pressure&lat={lat}&lon={lon}&zoom=8)"
            ]
            maps_text = "\n".join(map_links)
            message_text = (
                f"🗺 <b>𝗪𝗲𝗮𝘁𝗵𝗲𝗿 𝗠𝗮𝗽𝘀 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"{maps_text}"
            )
            try:
                await bot.edit_message_caption(
                    message_text, 
                    call.message.chat.id, 
                    call.message.message_id, 
                    reply_markup=InlineKeyboardMarkup(keyboard_back), 
                    parse_mode="HTML"
                )
            except ApiTelegramException:
                pass

        elif action == "refresh":
            cache_dir = os.path.join(os.getcwd(), "cache", "wth")
            new_image_path = os.path.join(cache_dir, f"weather_{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            executor.submit(create_weather_image, data, new_image_path).result()

            user = call.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            caption = (
                f"🔍 <b>𝗪𝗲𝗮𝘁𝗵𝗲𝗿 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"🌍 <b>𝗟𝗼𝗰𝗮𝘁𝗶𝗼𝗻:</b> {data['city']}, {data['country']}\n"
                f"🕒 <b>𝗧𝗶𝗺𝗲:</b> {data['current']['time']}\n"
                f"🌡 <b>𝗧𝗲𝗺𝗽:</b> {data['current']['temp']}°C\n"
                f"🌡 <b>𝗙𝗲𝗲𝗹𝘀 𝗟𝗶𝗸𝗲:</b> {data['current']['feels_like']}°C\n"
                f"💧 <b>𝗛𝘂𝗺𝗶𝗱𝗶𝘁𝘆:</b> {data['current']['humidity']}%\n"
                f"🌬 <b>𝗪𝗶𝗻𝗱:</b> {data['current']['wind_speed']} m/s from {data['current']['wind_dir']}°\n"
                f"🌅 <b>𝗦𝘂𝗻𝗿𝗶𝘀𝗲:</b> {data['current']['sunrise']}\n"
                f"🌇 <b>𝗦𝘂𝗻𝘀𝗲𝘁:</b> {data['current']['sunset']}\n"
                f"🌤 <b>𝗖𝗼𝗻𝗱𝗶𝘁𝗶𝗼𝗻:</b> {data['current']['weather']}\n"
                f"\n{footer}"
            )

            with open(new_image_path, "rb") as image_file:
                media = InputMediaPhoto(media=image_file, caption=caption, parse_mode="HTML")
                try:
                    await bot.edit_message_media(media, call.message.chat.id, call.message.message_id, reply_markup=reply_markup_main)
                except ApiTelegramException:
                    pass
            os.remove(new_image_path)

        elif action == "wth_menu":
            user = call.from_user
            username = f"@{user.username}" if user.username else user.first_name if user.first_name else str(user.id)
            footer = f"•──────────────────────•\n𝗥𝗲𝗾𝘂𝗲𝘀𝘁 𝗯𝘆: {username}"

            caption = (
                f"🔍 <b>𝗪𝗲𝗮𝘁𝗵𝗲𝗿 𝗳𝗼𝗿 {data['city']}</b>\n"
                f"<b>•──────────────────────•</b>\n"
                f"🌍 <b>𝗟𝗼𝗰𝗮𝘁𝗶𝗼𝗻:</b> {data['city']}, {data['country']}\n"
                f"🕒 <b>𝗧𝗶𝗺𝗲:</b> {data['current']['time']}\n"
                f"🌡 <b>𝗧𝗲𝗺𝗽:</b> {data['current']['temp']}°C\n"
                f"🌡 <b>𝗙𝗲𝗲𝗹𝘀 𝗟𝗶𝗸𝗲:</b> {data['current']['feels_like']}°C\n"
                f"💧 <b>𝗛𝘂𝗺𝗶𝗱𝗶𝘁𝘆:</b> {data['current']['humidity']}%\n"
                f"🌬 <b>𝗪𝗶𝗻𝗱:</b> {data['current']['wind_speed']} m/s from {data['current']['wind_dir']}°\n"
                f"🌅 <b>𝗦𝘂𝗻𝗿𝗶𝘀𝗲:</b> {data['current']['sunrise']}\n"
                f"🌇 <b>𝗦𝘂𝗻𝘀𝗲𝘁:</b> {data['current']['sunset']}\n"
                f"🌤 <b>𝗖𝗼𝗻𝗱𝗶𝘁𝗶𝗼𝗻:</b> {data['current']['weather']}\n"
                f"\n{footer}"
            )
            try:
                await bot.edit_message_caption(
                    caption, 
                    call.message.chat.id, 
                    call.message.message_id, 
                    reply_markup=reply_markup_main, 
                    parse_mode="HTML"
                )
            except ApiTelegramException:
                pass