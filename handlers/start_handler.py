import asyncio
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from broadcast.lang_manager import get_lang, set_lang, has_lang_set

CMDS_PER_PAGE = 8

CATEGORIES = [
    {
        "id": "ai",
        "name": {"en": "🤖 AI & Chat", "bn": "🤖 AI ও চ্যাট"},
        "cmds": [
            {
                "btn": {"en": "🔮 Gemini",      "bn": "🔮 জেমিনি"},
                "text": {
                    "en": "🔮 <b>Gemini AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.gem &lt;question&gt;</code>\nChat with Google Gemini AI\n\n📌 <b>Example:</b> <code>.gem What is the capital of Bangladesh?</code>",
                    "bn": "🔮 <b>Gemini AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.gem &lt;প্রশ্ন&gt;</code>\nGoogle Gemini AI দিয়ে চ্যাট করুন\n\n📌 <b>উদাহরণ:</b> <code>.gem বাংলাদেশের রাজধানী কী?</code>",
                },
            },
            {
                "btn": {"en": "💬 GPT",          "bn": "💬 GPT"},
                "text": {
                    "en": "💬 <b>GPT AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.gpt &lt;question&gt;</code>\nChat with OpenAI GPT\n\n📌 <b>Example:</b> <code>.gpt Write a poem about nature</code>",
                    "bn": "💬 <b>GPT AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.gpt &lt;প্রশ্ন&gt;</code>\nOpenAI GPT দিয়ে চ্যাট করুন\n\n📌 <b>উদাহরণ:</b> <code>.gpt প্রকৃতি নিয়ে একটি কবিতা লেখো</code>",
                },
            },
            {
                "btn": {"en": "🧠 Claude",       "bn": "🧠 ক্লড"},
                "text": {
                    "en": "🧠 <b>Claude AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.cld &lt;question&gt;</code>\nChat with Anthropic Claude AI\n\n📌 <b>Example:</b> <code>.cld Explain quantum computing</code>",
                    "bn": "🧠 <b>Claude AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.cld &lt;প্রশ্ন&gt;</code>\nAnthropic Claude AI দিয়ে চ্যাট করুন\n\n📌 <b>উদাহরণ:</b> <code>.cld কোয়ান্টাম কম্পিউটিং ব্যাখ্যা করো</code>",
                },
            },
            {
                "btn": {"en": "⚡ Grok",         "bn": "⚡ গ্রক"},
                "text": {
                    "en": "⚡ <b>Grok AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.grok &lt;question&gt;</code>\nChat with xAI Grok\n\n📌 <b>Example:</b> <code>.grok What is the meaning of life?</code>",
                    "bn": "⚡ <b>Grok AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.grok &lt;প্রশ্ন&gt;</code>\nxAI Grok দিয়ে চ্যাট করুন\n\n📌 <b>উদাহরণ:</b> <code>.grok জীবনের অর্থ কী?</code>",
                },
            },
            {
                "btn": {"en": "🌙 DeepSeek",     "bn": "🌙 ডিপসিক"},
                "text": {
                    "en": "🌙 <b>DeepSeek AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.ds &lt;question&gt;</code>\nChat with DeepSeek AI\n\n📌 <b>Example:</b> <code>.ds Write a short story</code>",
                    "bn": "🌙 <b>DeepSeek AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.ds &lt;প্রশ্ন&gt;</code>\nDeepSeek AI দিয়ে চ্যাট করুন\n\n📌 <b>উদাহরণ:</b> <code>.ds বাংলায় একটি গল্প লেখো</code>",
                },
            },
            {
                "btn": {"en": "🦙 Meta AI",      "bn": "🦙 মেটা AI"},
                "text": {
                    "en": "🦙 <b>Meta AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.meta &lt;question&gt;</code>\nChat with Meta LLaMA AI\n\n📌 <b>Example:</b> <code>.meta Tell me a joke</code>",
                    "bn": "🦙 <b>Meta AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.meta &lt;প্রশ্ন&gt;</code>\nMeta LLaMA AI দিয়ে চ্যাট করুন\n\n📌 <b>উদাহরণ:</b> <code>.meta একটি মজার জোকস বলো</code>",
                },
            },
            {
                "btn": {"en": "🐉 Qwen",         "bn": "🐉 কিউয়েন"},
                "text": {
                    "en": "🐉 <b>Qwen AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.qn &lt;question&gt;</code>\nChat with Alibaba Qwen AI\n\n📌 <b>Example:</b> <code>.qn Explain machine learning</code>",
                    "bn": "🐉 <b>Qwen AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.qn &lt;প্রশ্ন&gt;</code>\nAlibaba Qwen AI দিয়ে চ্যাট করুন\n\n📌 <b>উদাহরণ:</b> <code>.qn মেশিন লার্নিং ব্যাখ্যা করো</code>",
                },
            },
            {
                "btn": {"en": "🔍 Perplexity",   "bn": "🔍 পার্পলেক্সিটি"},
                "text": {
                    "en": "🔍 <b>Perplexity AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.pplx &lt;question&gt;</code>\nSearch the web with Perplexity AI\n\n📌 <b>Example:</b> <code>.pplx Latest news about AI</code>",
                    "bn": "🔍 <b>Perplexity AI</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.pplx &lt;প্রশ্ন&gt;</code>\nPerplexity AI দিয়ে ওয়েব সার্চ করুন\n\n📌 <b>উদাহরণ:</b> <code>.pplx AI নিয়ে সর্বশেষ খবর</code>",
                },
            },
            {
                "btn": {"en": "🔄 Auto Reply",   "bn": "🔄 অটো রিপ্লাই"},
                "text": {
                    "en": "🔄 <b>AI Auto Reply</b>\n━━━━━━━━━━━━━━━━━━\nToggle automatic AI replies on/off per AI:\n\n<code>.ongem</code> / <code>.offgem</code> — Gemini\n<code>.ongpt</code> / <code>.offgpt</code> — GPT\n<code>.oncld</code> / <code>.offcld</code> — Claude\n<code>.ongrok</code> / <code>.offgrok</code> — Grok\n<code>.onds</code> / <code>.offds</code> — DeepSeek\n<code>.onmeta</code> / <code>.offmeta</code> — Meta AI\n<code>.onqn</code> / <code>.offqn</code> — Qwen\n<code>.onpplx</code> / <code>.offpplx</code> — Perplexity",
                    "bn": "🔄 <b>AI অটো রিপ্লাই</b>\n━━━━━━━━━━━━━━━━━━\nযেকোনো AI এর অটো-রিপ্লাই চালু/বন্ধ করুন:\n\n<code>.ongem</code> / <code>.offgem</code> — Gemini\n<code>.ongpt</code> / <code>.offgpt</code> — GPT\n<code>.oncld</code> / <code>.offcld</code> — Claude\n<code>.ongrok</code> / <code>.offgrok</code> — Grok\n<code>.onds</code> / <code>.offds</code> — DeepSeek\n<code>.onmeta</code> / <code>.offmeta</code> — Meta AI\n<code>.onqn</code> / <code>.offqn</code> — Qwen\n<code>.onpplx</code> / <code>.offpplx</code> — Perplexity",
                },
            },
        ],
    },
    {
        "id": "dl",
        "name": {"en": "📥 Downloader", "bn": "📥 ডাউনলোডার"},
        "cmds": [
            {
                "btn": {"en": "▶️ YouTube",      "bn": "▶️ ইউটিউব"},
                "text": {
                    "en": "▶️ <b>YouTube Downloader</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.yt &lt;link&gt;</code>\nDownload YouTube videos\n\n📌 <b>Example:</b> <code>.yt https://youtu.be/xxx</code>",
                    "bn": "▶️ <b>YouTube ডাউনলোডার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.yt &lt;লিংক&gt;</code>\nYouTube ভিডিও ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.yt https://youtu.be/xxx</code>",
                },
            },
            {
                "btn": {"en": "🎬 All Video",    "bn": "🎬 সব ভিডিও"},
                "text": {
                    "en": "🎬 <b>All Video Downloader</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.dl &lt;link&gt;</code>\nDownload from Instagram, TikTok, Twitter & more\n\n📌 <b>Example:</b> <code>.dl https://instagram.com/reel/xxx</code>",
                    "bn": "🎬 <b>সব ভিডিও ডাউনলোডার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.dl &lt;লিংক&gt;</code>\nInstagram, TikTok, Twitter সহ যেকোনো ভিডিও\n\n📌 <b>উদাহরণ:</b> <code>.dl https://instagram.com/reel/xxx</code>",
                },
            },
            {
                "btn": {"en": "🎵 Spotify",      "bn": "🎵 স্পটিফাই"},
                "text": {
                    "en": "🎵 <b>Spotify Downloader</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.sp &lt;link or song name&gt;</code>\nDownload Spotify tracks\n\n📌 <b>Example:</b> <code>.sp Shape of You</code>",
                    "bn": "🎵 <b>Spotify ডাউনলোডার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.sp &lt;লিংক বা গানের নাম&gt;</code>\nSpotify গান ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.sp Shape of You</code>",
                },
            },
            {
                "btn": {"en": "📦 Terabox",      "bn": "📦 টেরাবক্স"},
                "text": {
                    "en": "📦 <b>Terabox Downloader</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.tbox &lt;link&gt;</code>\nDownload files from Terabox\n\n📌 <b>Example:</b> <code>.tbox https://terabox.com/xxx</code>",
                    "bn": "📦 <b>Terabox ডাউনলোডার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.tbox &lt;লিংক&gt;</code>\nTerabox থেকে ফাইল ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.tbox https://terabox.com/xxx</code>",
                },
            },
            {
                "btn": {"en": "📖 Story",         "bn": "📖 স্টোরি"},
                "text": {
                    "en": "📖 <b>Story Downloader</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.story &lt;link&gt;</code>\nDownload social media stories\n\n📌 <b>Example:</b> <code>.story https://instagram.com/stories/xxx</code>",
                    "bn": "📖 <b>স্টোরি ডাউনলোডার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.story &lt;লিংক&gt;</code>\nসোশ্যাল মিডিয়া স্টোরি ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.story https://instagram.com/stories/xxx</code>",
                },
            },
            {
                "btn": {"en": "🎨 Freepik",      "bn": "🎨 ফ্রিপিক"},
                "text": {
                    "en": "🎨 <b>Freepik Downloader</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.freepik &lt;link&gt;</code>\nDownload files from Freepik\n\n📌 <b>Example:</b> <code>.freepik https://freepik.com/xxx</code>",
                    "bn": "🎨 <b>Freepik ডাউনলোডার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.freepik &lt;লিংক&gt;</code>\nFreepik থেকে ফাইল ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.freepik https://freepik.com/xxx</code>",
                },
            },
            {
                "btn": {"en": "📚 Scribd",        "bn": "📚 স্ক্রিবড"},
                "text": {
                    "en": "📚 <b>Scribd Downloader</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.scribd &lt;link&gt;</code>\nDownload Scribd documents\n\n📌 <b>Example:</b> <code>.scribd https://scribd.com/doc/xxx</code>",
                    "bn": "📚 <b>Scribd ডাউনলোডার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.scribd &lt;লিংক&gt;</code>\nScribd ডকুমেন্ট ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.scribd https://scribd.com/doc/xxx</code>",
                },
            },
            {
                "btn": {"en": "👤 Profile Pic",  "bn": "👤 প্রোফাইল ছবি"},
                "text": {
                    "en": "👤 <b>Profile Picture</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.pp &lt;@username&gt;</code>\nDownload Telegram profile picture\n\n📌 <b>Example:</b> <code>.pp @durov</code> or reply to someone with <code>.pp</code>",
                    "bn": "👤 <b>প্রোফাইল পিকচার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.pp &lt;@username&gt;</code>\nটেলিগ্রাম প্রোফাইল পিকচার ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.pp @durov</code> বা কাউকে reply করে <code>.pp</code>",
                },
            },
            {
                "btn": {"en": "💻 Web Source",   "bn": "💻 ওয়েব সোর্স"},
                "text": {
                    "en": "💻 <b>Website Source Code</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.websrc &lt;URL&gt;</code>\nDownload a website's full source code\n\n📌 <b>Example:</b> <code>.websrc https://example.com</code>",
                    "bn": "💻 <b>ওয়েবসাইট সোর্স কোড</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.websrc &lt;URL&gt;</code>\nওয়েবসাইটের সম্পূর্ণ সোর্স কোড ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.websrc https://example.com</code>",
                },
            },
            {
                "btn": {"en": "🖼️ YT Thumbnail", "bn": "🖼️ থাম্বনেইল"},
                "text": {
                    "en": "🖼️ <b>YouTube Thumbnail</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.yth &lt;link&gt;</code>\nGet the thumbnail of any YouTube video\n\n📌 <b>Example:</b> <code>.yth https://youtu.be/xxx</code>",
                    "bn": "🖼️ <b>YouTube থাম্বনেইল</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.yth &lt;লিংক&gt;</code>\nYouTube ভিডিওর থাম্বনেইল ডাউনলোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.yth https://youtu.be/xxx</code>",
                },
            },
        ],
    },
    {
        "id": "media",
        "name": {"en": "🎨 Image & Media", "bn": "🎨 ছবি ও মিডিয়া"},
        "cmds": [
            {
                "btn": {"en": "🖼️ AI Image",     "bn": "🖼️ AI ছবি"},
                "text": {
                    "en": "🖼️ <b>AI Image Generator</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.imagine &lt;prompt&gt;</code>\nGenerate images using AI\n\n📌 <b>Example:</b> <code>.imagine a sunset over mountains in anime style</code>",
                    "bn": "🖼️ <b>AI ছবি জেনারেটর</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.imagine &lt;prompt&gt;</code>\nAI দিয়ে ছবি তৈরি করুন\n\n📌 <b>উদাহরণ:</b> <code>.imagine a sunset over mountains in anime style</code>",
                },
            },
            {
                "btn": {"en": "✂️ BG Remove",    "bn": "✂️ ব্যাকগ্রাউন্ড"},
                "text": {
                    "en": "✂️ <b>Background Remover</b>\n━━━━━━━━━━━━━━━━━━\nSend a photo with caption <code>.bgremove</code>\nRemoves the background from your photo",
                    "bn": "✂️ <b>ব্যাকগ্রাউন্ড রিমুভার</b>\n━━━━━━━━━━━━━━━━━━\nছবি পাঠান, ক্যাপশনে <code>.bgremove</code> লিখুন\nছবির ব্যাকগ্রাউন্ড সরিয়ে দেবে",
                },
            },
            {
                "btn": {"en": "✨ Enhance",       "bn": "✨ এনহান্স"},
                "text": {
                    "en": "✨ <b>Face Enhancer</b>\n━━━━━━━━━━━━━━━━━━\nSend a photo with caption <code>.enh</code>\nEnhances and upscales face quality",
                    "bn": "✨ <b>ফেস এনহান্সার</b>\n━━━━━━━━━━━━━━━━━━\nছবি পাঠান, ক্যাপশনে <code>.enh</code> লিখুন\nফেস এনহান্স করে ছবির মান উন্নত করবে",
                },
            },
            {
                "btn": {"en": "🔄 Face Swap",    "bn": "🔄 ফেস সোয়াপ"},
                "text": {
                    "en": "🔄 <b>Face Swap</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.faceswap</code>\nSend two photos — first the source face, then the target\nThe bot will swap the faces",
                    "bn": "🔄 <b>ফেস সোয়াপ</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.faceswap</code>\nদুটো ছবি পাঠান — প্রথমটা source, দ্বিতীয়টা target\nবট ফেস বদলে দেবে",
                },
            },
            {
                "btn": {"en": "📝 OCR",           "bn": "📝 OCR"},
                "text": {
                    "en": "📝 <b>Image to Text (OCR)</b>\n━━━━━━━━━━━━━━━━━━\nSend an image with caption <code>.ocr</code>\nExtracts all text from the image",
                    "bn": "📝 <b>ছবি থেকে টেক্সট (OCR)</b>\n━━━━━━━━━━━━━━━━━━\nছবি পাঠান, ক্যাপশনে <code>.ocr</code> লিখুন\nছবি থেকে সব টেক্সট বের করবে",
                },
            },
            {
                "btn": {"en": "💡 Img Prompt",   "bn": "💡 ইমেজ প্রম্পট"},
                "text": {
                    "en": "💡 <b>Image to Prompt</b>\n━━━━━━━━━━━━━━━━━━\nSend an image with caption <code>.prompt</code>\nGenerates an AI prompt describing your image",
                    "bn": "💡 <b>ছবি থেকে প্রম্পট</b>\n━━━━━━━━━━━━━━━━━━\nছবি পাঠান, ক্যাপশনে <code>.prompt</code> লিখুন\nছবির AI প্রম্পট তৈরি করে দেবে",
                },
            },
            {
                "btn": {"en": "🔃 Converter",    "bn": "🔃 কনভার্টার"},
                "text": {
                    "en": "🔃 <b>File Converter</b>\n━━━━━━━━━━━━━━━━━━\nSend a file with caption <code>.conv</code>\nConverts video, audio, or image formats",
                    "bn": "🔃 <b>ফাইল কনভার্টার</b>\n━━━━━━━━━━━━━━━━━━\nফাইল পাঠান, ক্যাপশনে <code>.conv</code> লিখুন\nভিডিও, অডিও বা ইমেজ ফরম্যাট কনভার্ট করবে",
                },
            },
            {
                "btn": {"en": "📱 QR Code",      "bn": "📱 QR কোড"},
                "text": {
                    "en": "📱 <b>QR Code</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.qr &lt;text or link&gt;</code>\nGenerate a QR code, or send a QR image to scan it\n\n📌 <b>Example:</b> <code>.qr https://t.me/yourbot</code>",
                    "bn": "📱 <b>QR কোড</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.qr &lt;টেক্সট বা লিংক&gt;</code>\nQR কোড তৈরি করুন, বা QR ছবি পাঠিয়ে স্ক্যান করুন\n\n📌 <b>উদাহরণ:</b> <code>.qr https://t.me/yourbot</code>",
                },
            },
            {
                "btn": {"en": "🔊 Text→Voice",   "bn": "🔊 টেক্সট→ভয়েস"},
                "text": {
                    "en": "🔊 <b>Text to Voice</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.say &lt;text&gt;</code>\nConvert text to a voice message\n\n📌 <b>Example:</b> <code>.say Hello, how are you?</code>",
                    "bn": "🔊 <b>টেক্সট টু ভয়েস</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.say &lt;টেক্সট&gt;</code>\nটেক্সট থেকে ভয়েস মেসেজ তৈরি করুন\n\n📌 <b>উদাহরণ:</b> <code>.say আমি ভালো আছি, তুমি কেমন আছো?</code>",
                },
            },
            {
                "btn": {"en": "📤 Share File",   "bn": "📤 শেয়ার ফাইল"},
                "text": {
                    "en": "📤 <b>File Share</b>\n━━━━━━━━━━━━━━━━━━\nSend a file with caption <code>.share</code>\nGet a permanent download link for your file",
                    "bn": "📤 <b>ফাইল শেয়ার</b>\n━━━━━━━━━━━━━━━━━━\nফাইল পাঠান, ক্যাপশনে <code>.share</code> লিখুন\nফাইলের একটি পার্মানেন্ট ডাউনলোড লিংক পাবেন",
                },
            },
            {
                "btn": {"en": "🎭 Sticker",      "bn": "🎭 স্টিকার"},
                "text": {
                    "en": "🎭 <b>Sticker Tools</b>\n━━━━━━━━━━━━━━━━━━\n<code>.sticker</code> — Create a sticker (send photo/video)\n<code>.mypacks</code> — List your sticker packs\n<code>.newpack &lt;name&gt;</code> — Create a new pack\n<code>.delpack</code> — Delete a pack\n<code>.packrenm</code> — Rename a pack",
                    "bn": "🎭 <b>স্টিকার টুলস</b>\n━━━━━━━━━━━━━━━━━━\n<code>.sticker</code> — স্টিকার বানান (ছবি/ভিডিও পাঠান)\n<code>.mypacks</code> — আপনার সব প্যাক দেখুন\n<code>.newpack &lt;নাম&gt;</code> — নতুন প্যাক বানান\n<code>.delpack</code> — প্যাক ডিলিট করুন\n<code>.packrenm</code> — প্যাক রিনেম করুন",
                },
            },
            {
                "btn": {"en": "☁️ Upload",       "bn": "☁️ আপলোড"},
                "text": {
                    "en": "☁️ <b>File Upload</b>\n━━━━━━━━━━━━━━━━━━\nSend a file with caption <code>.upload</code>\nUploads your file to the cloud and gives a download link",
                    "bn": "☁️ <b>ফাইল আপলোড</b>\n━━━━━━━━━━━━━━━━━━\nফাইল পাঠান, ক্যাপশনে <code>.upload</code> লিখুন\nক্লাউডে আপলোড করে ডাউনলোড লিংক দেবে",
                },
            },
            {
                "btn": {"en": "🎵 Vocal Remover", "bn": "🎵 ভোকাল রিমুভার"},
                "text": {
                    "en": "🎵 <b>Vocal Remover</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.vocal</code> or <code>.vrm</code>\nReply to an audio/video file to separate vocals from the instrumental track\n\n📌 <b>Aliases:</b> <code>.vrm</code> · <code>.remover</code>",
                    "bn": "🎵 <b>ভোকাল রিমুভার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.vocal</code> বা <code>.vrm</code>\nঅডিও/ভিডিও ফাইলে রিপ্লাই দিন — ভোকাল ও ইন্সট্রুমেন্টাল আলাদা করে দেবে\n\n📌 <b>এলিয়াস:</b> <code>.vrm</code> · <code>.remover</code>",
                },
            },
        ],
    },
    {
        "id": "util",
        "name": {"en": "⚙️ Utility & Info", "bn": "⚙️ ইউটিলিটি ও তথ্য"},
        "cmds": [
            {
                "btn": {"en": "ℹ️ User Info",    "bn": "ℹ️ ইউজার তথ্য"},
                "text": {
                    "en": "ℹ️ <b>User Info</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.info</code>\nView your own or another user's info\nReply to someone's message to see their info",
                    "bn": "ℹ️ <b>ইউজার তথ্য</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.info</code>\nআপনার বা অন্য কারো তথ্য দেখুন\nকাউকে reply করে <code>.info</code> দিন",
                },
            },
            {
                "btn": {"en": "🎭 Fake Address", "bn": "🎭 ফেক এড্রেস"},
                "text": {
                    "en": "🎭 <b>Fake Address Generator</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.fake &lt;country code&gt;</code>\nGenerate a fake identity\n\n📌 <b>Example:</b> <code>.fake US</code> or <code>.fake BD</code>",
                    "bn": "🎭 <b>ফেক এড্রেস জেনারেটর</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.fake &lt;দেশের কোড&gt;</code>\nফেক পরিচয় তৈরি করুন\n\n📌 <b>উদাহরণ:</b> <code>.fake US</code> বা <code>.fake BD</code>",
                },
            },
            {
                "btn": {"en": "🌤️ Weather",      "bn": "🌤️ আবহাওয়া"},
                "text": {
                    "en": "🌤️ <b>Weather Info</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.wth &lt;city&gt;</code>\nGet current weather for any city\n\n📌 <b>Example:</b> <code>.wth Dhaka</code>",
                    "bn": "🌤️ <b>আবহাওয়া তথ্য</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.wth &lt;শহর&gt;</code>\nযেকোনো শহরের আবহাওয়ার তথ্য পান\n\n📌 <b>উদাহরণ:</b> <code>.wth Dhaka</code>",
                },
            },
            {
                "btn": {"en": "🌐 Translate",    "bn": "🌐 অনুবাদ"},
                "text": {
                    "en": "🌐 <b>Text Translator</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.tr &lt;lang code&gt; &lt;text&gt;</code>\nTranslate text to any language\n\n📌 <b>Example:</b> <code>.tr en আমি ভালো আছি</code>",
                    "bn": "🌐 <b>টেক্সট অনুবাদক</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.tr &lt;ভাষা কোড&gt; &lt;টেক্সট&gt;</code>\nযেকোনো ভাষায় অনুবাদ করুন\n\n📌 <b>উদাহরণ:</b> <code>.tr en আমি ভালো আছি</code>",
                },
            },
            {
                "btn": {"en": "🌍 Website SS",   "bn": "🌍 ওয়েবসাইট SS"},
                "text": {
                    "en": "🌍 <b>Website Screenshot</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.site &lt;URL&gt;</code>\nTake a screenshot of any website\n\n📌 <b>Example:</b> <code>.site https://google.com</code>",
                    "bn": "🌍 <b>ওয়েবসাইট স্ক্রিনশট</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.site &lt;URL&gt;</code>\nযেকোনো ওয়েবসাইটের স্ক্রিনশট পান\n\n📌 <b>উদাহরণ:</b> <code>.site https://google.com</code>",
                },
            },
            {
                "btn": {"en": "🔗 Domain",       "bn": "🔗 ডোমেইন"},
                "text": {
                    "en": "🔗 <b>Domain Info</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.domain &lt;domain&gt;</code> or <code>.dmn &lt;domain&gt;</code>\nGet WHOIS & DNS info for any domain\n\n📌 <b>Example:</b> <code>.domain google.com</code>",
                    "bn": "🔗 <b>ডোমেইন তথ্য</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.domain &lt;ডোমেইন&gt;</code> বা <code>.dmn &lt;ডোমেইন&gt;</code>\nDomain WHOIS ও DNS তথ্য পান\n\n📌 <b>উদাহরণ:</b> <code>.domain google.com</code>",
                },
            },
            {
                "btn": {"en": "💣 SMS Bomb",     "bn": "💣 SMS বোম্ব"},
                "text": {
                    "en": "💣 <b>SMS Bomb</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.bomb &lt;number&gt; &lt;count&gt;</code>\nSend SMS spam to a number\n\n📌 <b>Example:</b> <code>.bomb 01XXXXXXXXX 10</code>",
                    "bn": "💣 <b>SMS বোম্ব</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.bomb &lt;নম্বর&gt; &lt;সংখ্যা&gt;</code>\nকোনো নম্বরে SMS বোম্ব পাঠান\n\n📌 <b>উদাহরণ:</b> <code>.bomb 01XXXXXXXXX 10</code>",
                },
            },
            {
                "btn": {"en": "📄 Spam Text",    "bn": "📄 স্প্যাম টেক্সট"},
                "text": {
                    "en": "📄 <b>Spam Text File</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.spmtxt &lt;text&gt; &lt;count&gt;</code>\nCreate a spam text file\n\n📌 <b>Example:</b> <code>.spmtxt Hello 100</code>",
                    "bn": "📄 <b>স্প্যাম টেক্সট ফাইল</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.spmtxt &lt;টেক্সট&gt; &lt;সংখ্যা&gt;</code>\nস্প্যাম টেক্সট ফাইল তৈরি করুন\n\n📌 <b>উদাহরণ:</b> <code>.spmtxt Hello 100</code>",
                },
            },
            {
                "btn": {"en": "🐙 GitHub",       "bn": "🐙 গিটহাব"},
                "text": {
                    "en": "🐙 <b>GitHub Search</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.github &lt;search term&gt;</code>\nSearch GitHub repositories\n\n📌 <b>Example:</b> <code>.github python telegram bot</code>",
                    "bn": "🐙 <b>GitHub সার্চ</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.github &lt;সার্চ টার্ম&gt;</code>\nGitHub রিপোজিটরি সার্চ করুন\n\n📌 <b>উদাহরণ:</b> <code>.github python telegram bot</code>",
                },
            },
            {
                "btn": {"en": "🎥 Movie",        "bn": "🎥 মুভি"},
                "text": {
                    "en": "🎥 <b>Movie Search</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.movie &lt;movie name&gt;</code>\nSearch movie ratings and info\n\n📌 <b>Example:</b> <code>.movie Inception</code>",
                    "bn": "🎥 <b>মুভি সার্চ</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.movie &lt;মুভির নাম&gt;</code>\nমুভির রেটিং ও তথ্য পান\n\n📌 <b>উদাহরণ:</b> <code>.movie Inception</code>",
                },
            },
            {
                "btn": {"en": "💱 Currency",     "bn": "💱 কারেন্সি"},
                "text": {
                    "en": "💱 <b>Currency Converter</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.exchange &lt;amount&gt; &lt;from&gt; &lt;to&gt;</code>\nConvert between currencies\n\n📌 <b>Example:</b> <code>.exchange 100 USD BDT</code>",
                    "bn": "💱 <b>কারেন্সি কনভার্টার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.exchange &lt;পরিমাণ&gt; &lt;থেকে&gt; &lt;তে&gt;</code>\nকারেন্সি কনভার্ট করুন\n\n📌 <b>উদাহরণ:</b> <code>.exchange 100 USD BDT</code>",
                },
            },
            {
                "btn": {"en": "🔐 2FA Auth",     "bn": "🔐 2FA অথ"},
                "text": {
                    "en": "🔐 <b>2FA Authenticator</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.2fa &lt;secret key&gt;</code>\nGet 2FA TOTP code\n\n📌 <b>Example:</b> <code>.2fa JBSWY3DPEHPK3PXP</code>",
                    "bn": "🔐 <b>2FA অথেন্টিকেটর</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.2fa &lt;secret key&gt;</code>\n2FA TOTP কোড পান\n\n📌 <b>উদাহরণ:</b> <code>.2fa JBSWY3DPEHPK3PXP</code>",
                },
            },
            {
                "btn": {"en": "📧 Temp Mail",    "bn": "📧 টেম্প মেইল"},
                "text": {
                    "en": "📧 <b>Temporary Email</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.tmail</code>\nGet a disposable temporary email and check its inbox",
                    "bn": "📧 <b>টেম্পোরারি ইমেইল</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.tmail</code>\nটেম্পোরারি ইমেইল পান এবং ইনবক্স চেক করুন",
                },
            },
            {
                "btn": {"en": "📬 Gmail Check",  "bn": "📬 জিমেইল চেক"},
                "text": {
                    "en": "📬 <b>Gmail Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.cgmail &lt;email:password&gt;</code>\nCheck a Gmail account\n\n📌 <b>Example:</b> <code>.cgmail test@gmail.com:pass123</code>",
                    "bn": "📬 <b>Gmail চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.cgmail &lt;email:password&gt;</code>\nGmail অ্যাকাউন্ট চেক করুন\n\n📌 <b>উদাহরণ:</b> <code>.cgmail test@gmail.com:pass123</code>",
                },
            },
            {
                "btn": {"en": "🔑 Session",      "bn": "🔑 সেশন"},
                "text": {
                    "en": "🔑 <b>Session String Generator</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.string</code>\nGenerate a Pyrogram/Telethon session string",
                    "bn": "🔑 <b>সেশন স্ট্রিং জেনারেটর</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.string</code>\nPyrogram/Telethon সেশন স্ট্রিং তৈরি করুন",
                },
            },
            {
                "btn": {"en": "🛡️ TG Auth",      "bn": "🛡️ TG অথ"},
                "text": {
                    "en": "🛡️ <b>Telegram Auth</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.tgauth</code>\nGet your Telegram API ID & Hash",
                    "bn": "🛡️ <b>Telegram অথ</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.tgauth</code>\nTelegram API ID ও Hash পান",
                },
            },
            {
                "btn": {"en": "📱 Temp Number",   "bn": "📱 টেম্প নম্বর"},
                "text": {
                    "en": "📱 <b>Temp Number</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.tnumber</code>\nGet a free temporary phone number and receive OTPs\n\n📌 Browse by country and pick a number to view incoming messages",
                    "bn": "📱 <b>টেম্প নম্বর</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.tnumber</code>\nফ্রি টেম্পোরারি ফোন নম্বর পান এবং OTP রিসিভ করুন\n\n📌 দেশ বেছে নম্বর সিলেক্ট করুন, ইনকামিং মেসেজ দেখুন",
                },
            },
            {
                "btn": {"en": "📦 Base64",       "bn": "📦 Base64"},
                "text": {
                    "en": "📦 <b>Base64 Tool</b>\n━━━━━━━━━━━━━━━━━━\n<code>.b64encode &lt;text&gt;</code> — Encode text\n<code>.b64decode &lt;text&gt;</code> — Decode text\n\n📌 <b>Example:</b> <code>.b64encode Hello World</code>",
                    "bn": "📦 <b>Base64 টুল</b>\n━━━━━━━━━━━━━━━━━━\n<code>.b64encode &lt;টেক্সট&gt;</code> — এনকোড করুন\n<code>.b64decode &lt;টেক্সট&gt;</code> — ডিকোড করুন\n\n📌 <b>উদাহরণ:</b> <code>.b64encode Hello World</code>",
                },
            },
            {
                "btn": {"en": "📞 Truecaller",   "bn": "📞 ট্রুকলার"},
                "text": {
                    "en": "📞 <b>Truecaller Check</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.tc &lt;number&gt;</code>\nLook up a phone number on Truecaller\n\n📌 <b>Example:</b> <code>.tc +8801XXXXXXXXX</code>",
                    "bn": "📞 <b>Truecaller চেক</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.tc &lt;নম্বর&gt;</code>\nTruecaller দিয়ে নম্বর সার্চ করুন\n\n📌 <b>উদাহরণ:</b> <code>.tc +8801XXXXXXXXX</code>",
                },
            },
            {
                "btn": {"en": "🔒 Proxy",        "bn": "🔒 প্রক্সি"},
                "text": {
                    "en": "🔒 <b>Proxy Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.px &lt;proxy&gt;</code>\nCheck if a proxy is working\n\n📌 <b>Example:</b> <code>.px 1.2.3.4:8080</code>",
                    "bn": "🔒 <b>প্রক্সি চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.px &lt;proxy&gt;</code>\nProxy চেক করুন\n\n📌 <b>উদাহরণ:</b> <code>.px 1.2.3.4:8080</code>",
                },
            },
        ],
    },
    {
        "id": "card",
        "name": {"en": "💳 Carding & BIN", "bn": "💳 কার্ডিং ও BIN"},
        "cmds": [
            {
                "btn": {"en": "🎰 Card Gen",     "bn": "🎰 কার্ড জেন"},
                "text": {
                    "en": "🎰 <b>Card Generator</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.gen &lt;BIN&gt;</code>\nGenerate card numbers from a BIN\n\n📌 <b>Example:</b> <code>.gen 414720</code>",
                    "bn": "🎰 <b>কার্ড জেনারেটর</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.gen &lt;BIN&gt;</code>\nBIN দিয়ে কার্ড নম্বর জেনারেট করুন\n\n📌 <b>উদাহরণ:</b> <code>.gen 414720</code>",
                },
            },
            {
                "btn": {"en": "✅ Card Check",   "bn": "✅ কার্ড চেক"},
                "text": {
                    "en": "✅ <b>Card Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.chk &lt;card&gt;</code>\nCheck a card\n\n📌 <b>Format:</b> <code>.chk 4147201234567890|12|25|123</code>",
                    "bn": "✅ <b>কার্ড চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.chk &lt;card&gt;</code>\nকার্ড চেক করুন\n\n📌 <b>ফরম্যাট:</b> <code>.chk 4147201234567890|12|25|123</code>",
                },
            },
            {
                "btn": {"en": "📋 Mass Check",   "bn": "📋 ম্যাস চেক"},
                "text": {
                    "en": "📋 <b>Mass Card Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.mas</code> (send a card list file)\nCheck multiple cards at once",
                    "bn": "📋 <b>ম্যাস কার্ড চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.mas</code> (কার্ড লিস্ট ফাইল পাঠান)\nএকসাথে অনেক কার্ড চেক করুন",
                },
            },
            {
                "btn": {"en": "💰 Stripe",       "bn": "💰 স্ট্রাইপ"},
                "text": {
                    "en": "💰 <b>Stripe Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.st &lt;card&gt;</code>\nCheck card via Stripe gateway\n\n📌 <b>Format:</b> <code>.st 4147201234567890|12|25|123</code>",
                    "bn": "💰 <b>Stripe চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.st &lt;card&gt;</code>\nStripe গেটওয়ে দিয়ে কার্ড চেক করুন\n\n📌 <b>ফরম্যাট:</b> <code>.st 4147201234567890|12|25|123</code>",
                },
            },
            {
                "btn": {"en": "📊 Mass Stripe",  "bn": "📊 ম্যাস স্ট্রাইপ"},
                "text": {
                    "en": "📊 <b>Mass Stripe Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.mst</code> (send a card list file)\nCheck multiple cards via Stripe at once",
                    "bn": "📊 <b>ম্যাস Stripe চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.mst</code> (কার্ড লিস্ট ফাইল পাঠান)\nStripe দিয়ে অনেক কার্ড একসাথে চেক করুন",
                },
            },
            {
                "btn": {"en": "🔵 B3 Check",     "bn": "🔵 B3 চেক"},
                "text": {
                    "en": "🔵 <b>B3 Gateway Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.b3 &lt;card&gt;</code>\nCheck card via B3 gateway\n\n📌 <b>Format:</b> <code>.b3 4147201234567890|12|25|123</code>",
                    "bn": "🔵 <b>B3 গেটওয়ে চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.b3 &lt;card&gt;</code>\nB3 গেটওয়ে দিয়ে কার্ড চেক করুন\n\n📌 <b>ফরম্যাট:</b> <code>.b3 4147201234567890|12|25|123</code>",
                },
            },
            {
                "btn": {"en": "📈 Mass B3",      "bn": "📈 ম্যাস B3"},
                "text": {
                    "en": "📈 <b>Mass B3 Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.mb3</code> (send a card list file)\nCheck multiple cards via B3 at once",
                    "bn": "📈 <b>ম্যাস B3 চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.mb3</code> (কার্ড লিস্ট ফাইল পাঠান)\nB3 দিয়ে অনেক কার্ড একসাথে চেক করুন",
                },
            },
            {
                "btn": {"en": "🏦 BIN Info",     "bn": "🏦 BIN তথ্য"},
                "text": {
                    "en": "🏦 <b>BIN Lookup</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.bin &lt;BIN&gt;</code>\nGet BIN info: bank, country, card type\n\n📌 <b>Example:</b> <code>.bin 414720</code>",
                    "bn": "🏦 <b>BIN লুকআপ</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.bin &lt;BIN&gt;</code>\nBIN তথ্য পান: ব্যাংক, দেশ, কার্ড টাইপ\n\n📌 <b>উদাহরণ:</b> <code>.bin 414720</code>",
                },
            },
            {
                "btn": {"en": "🏛️ IBAN",         "bn": "🏛️ IBAN"},
                "text": {
                    "en": "🏛️ <b>IBAN Generator</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.iban &lt;country code&gt;</code>\nGenerate an IBAN number\n<code>.ibncntry</code> — See country list\n\n📌 <b>Example:</b> <code>.iban DE</code>",
                    "bn": "🏛️ <b>IBAN জেনারেটর</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.iban &lt;দেশ কোড&gt;</code>\nIBAN জেনারেট করুন\n<code>.ibncntry</code> — সব দেশ দেখুন\n\n📌 <b>উদাহরণ:</b> <code>.iban DE</code>",
                },
            },
            {
                "btn": {"en": "🆔 CPF Info",     "bn": "🆔 CPF তথ্য"},
                "text": {
                    "en": "🆔 <b>CPF Lookup</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.cpf &lt;CPF number&gt;</code>\nCheck Brazilian CPF information\n\n📌 <b>Example:</b> <code>.cpf 12345678901</code>",
                    "bn": "🆔 <b>CPF লুকআপ</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.cpf &lt;CPF নম্বর&gt;</code>\nBrazilian CPF তথ্য চেক করুন\n\n📌 <b>উদাহরণ:</b> <code>.cpf 12345678901</code>",
                },
            },
            {
                "btn": {"en": "🏦 Routing",      "bn": "🏦 রাউটিং"},
                "text": {
                    "en": "🏦 <b>Routing Checker</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.rut &lt;routing number&gt;</code>\nGet bank routing information\n\n📌 <b>Example:</b> <code>.rut 021000021</code>",
                    "bn": "🏦 <b>রাউটিং চেকার</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.rut &lt;routing নম্বর&gt;</code>\nBank routing তথ্য পান\n\n📌 <b>উদাহরণ:</b> <code>.rut 021000021</code>",
                },
            },
        ],
    },
    {
        "id": "admin",
        "name": {"en": "👤 Admin & System", "bn": "👤 অ্যাডমিন ও সিস্টেম"},
        "cmds": [
            {
                "btn": {"en": "📢 Broadcast",    "bn": "📢 ব্রডকাস্ট"},
                "text": {
                    "en": "📢 <b>Broadcast</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.bc &lt;message&gt;</code>\n(Admin only) Send a message to all users",
                    "bn": "📢 <b>ব্রডকাস্ট</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.bc &lt;বার্তা&gt;</code>\n(শুধুমাত্র Admin) সব ইউজারকে মেসেজ পাঠান",
                },
            },
            {
                "btn": {"en": "📊 Bot Stats",    "bn": "📊 বট স্ট্যাটস"},
                "text": {
                    "en": "📊 <b>Bot Statistics</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.stats</code>\n(Admin only) View user count and bot stats",
                    "bn": "📊 <b>বট স্ট্যাটিস্টিক্স</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.stats</code>\n(শুধুমাত্র Admin) ইউজার সংখ্যা ও বট স্ট্যাটস দেখুন",
                },
            },
            {
                "btn": {"en": "📁 User Data",    "bn": "📁 ইউজার ডেটা"},
                "text": {
                    "en": "📁 <b>User Database</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.usersfile</code>\n(Admin only) Download the user database file",
                    "bn": "📁 <b>ইউজার ডেটাবেস</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.usersfile</code>\n(শুধুমাত্র Admin) ইউজার ডেটাবেস ফাইল ডাউনলোড করুন",
                },
            },
            {
                "btn": {"en": "🚫 Ban/Unban",    "bn": "🚫 ব্যান/আনব্যান"},
                "text": {
                    "en": "🚫 <b>Ban / Unban User</b>\n━━━━━━━━━━━━━━━━━━\n(Admin only)\n<code>.fuck &lt;user_id&gt;</code> — Ban a user\n<code>.cumin &lt;user_id&gt;</code> — Unban a user",
                    "bn": "🚫 <b>ব্যান / আনব্যান ইউজার</b>\n━━━━━━━━━━━━━━━━━━\n(শুধুমাত্র Admin)\n<code>.fuck &lt;user_id&gt;</code> — ইউজার ব্যান করুন\n<code>.cumin &lt;user_id&gt;</code> — ইউজার আনব্যান করুন",
                },
            },
            {
                "btn": {"en": "🎭 Reveal",       "bn": "🎭 রিভিল"},
                "text": {
                    "en": "🎭 <b>Reveal</b>\n━━━━━━━━━━━━━━━━━━\n<b>Command:</b> <code>.reveal</code>\nView hidden information",
                    "bn": "🎭 <b>রিভিল</b>\n━━━━━━━━━━━━━━━━━━\n<b>কমান্ড:</b> <code>.reveal</code>\nহিডেন তথ্য দেখুন",
                },
            },
        ],
    },
]

_CAT_MAP = {cat["id"]: cat for cat in CATEGORIES}

# ── UI strings ────────────────────────────────────────────────────────────────
_UI = {
    "en": {
        "lang_prompt":     "🌐 <b>Welcome!</b>\n━━━━━━━━━━━━━━━━━━━━━━\nPlease select your preferred language.\nআপনার পছন্দের ভাষা বেছে নিন।",
        "lang_set_en":     "✅ Language set to <b>English</b>!",
        "lang_set_bn":     "✅ ভাষা <b>বাংলা</b>তে সেট করা হয়েছে!",
        "welcome":         "👋 <b>Welcome, {name}!</b>",
        "user_id":         "🆔 <b>User ID :</b>",
        "chat_id":         "💬 <b>Chat ID :</b>",
        "uname":           "👤 <b>Name    :</b>",
        "pick_cat":        "📂 <b>Select a category:</b>",
        "pick_cmd":        "📋 Select a command",
        "page":            "Page {cur}/{total}",
        "back_btn":        "🔙 Back",
        "home_btn":        "🏠 Home",
        "prev_btn":        "⬅️ Prev",
        "next_btn":        "➡️ Next",
        "lang_btn":        "🌐 Language",
        "change_lang":     "🌐 <b>Change Language</b>\n━━━━━━━━━━━━━━━━━━━━━━\nSelect your preferred language:",
    },
    "bn": {
        "lang_prompt":     "🌐 <b>Welcome!</b>\n━━━━━━━━━━━━━━━━━━━━━━\nPlease select your preferred language.\nআপনার পছন্দের ভাষা বেছে নিন।",
        "lang_set_en":     "✅ Language set to <b>English</b>!",
        "lang_set_bn":     "✅ ভাষা <b>বাংলা</b>তে সেট করা হয়েছে!",
        "welcome":         "👋 <b>স্বাগতম, {name}!</b>",
        "user_id":         "🆔 <b>ইউজার আইডি:</b>",
        "chat_id":         "💬 <b>চ্যাট আইডি:</b>",
        "uname":           "👤 <b>নাম         :</b>",
        "pick_cat":        "📂 <b>একটি ক্যাটাগরি বেছে নিন:</b>",
        "pick_cmd":        "📋 কমান্ড বেছে নিন",
        "page":            "Page {cur}/{total}",
        "back_btn":        "🔙 ফিরে যান",
        "home_btn":        "🏠 হোম",
        "prev_btn":        "⬅️ আগে",
        "next_btn":        "➡️ পরে",
        "lang_btn":        "🌐 ভাষা পরিবর্তন",
        "change_lang":     "🌐 <b>ভাষা পরিবর্তন</b>\n━━━━━━━━━━━━━━━━━━━━━━\nআপনার পছন্দের ভাষা বেছে নিন:",
    },
}


def ui(lang, key, **kw):
    text = _UI.get(lang, _UI["en"]).get(key, key)
    return text.format(**kw) if kw else text


# ── Markup builders ───────────────────────────────────────────────────────────

def _lang_select_markup():
    m = InlineKeyboardMarkup()
    m.row(
        InlineKeyboardButton("🇧🇩 বাংলা",  callback_data="lang_select:bn"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_select:en"),
    )
    return m


def _home_markup(lang):
    m = InlineKeyboardMarkup()
    row = []
    for cat in CATEGORIES:
        btn = InlineKeyboardButton(cat["name"][lang], callback_data=f"cat:{cat['id']}:0")
        row.append(btn)
        if len(row) == 2:
            m.row(*row)
            row = []
    if row:
        m.row(*row)
    m.row(InlineKeyboardButton(ui(lang, "lang_btn"), callback_data="change_lang"))
    return m


def _category_markup(cat_id, page, lang):
    cat = _CAT_MAP[cat_id]
    cmds = cat["cmds"]
    total = len(cmds)
    total_pages = max(1, (total + CMDS_PER_PAGE - 1) // CMDS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * CMDS_PER_PAGE
    end = min(start + CMDS_PER_PAGE, total)

    m = InlineKeyboardMarkup()
    row = []
    for i in range(start, end):
        label = cmds[i]["btn"][lang]
        row.append(InlineKeyboardButton(label, callback_data=f"cmd:{cat_id}:{i}"))
        if len(row) == 2:
            m.row(*row)
            row = []
    if row:
        m.row(*row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(ui(lang, "prev_btn"), callback_data=f"cat:{cat_id}:{page - 1}"))
    nav.append(InlineKeyboardButton(ui(lang, "home_btn"), callback_data="home"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(ui(lang, "next_btn"), callback_data=f"cat:{cat_id}:{page + 1}"))
    m.row(*nav)

    return m, page, total_pages


def _cmd_markup(cat_id, cmd_idx, lang):
    page = cmd_idx // CMDS_PER_PAGE
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(ui(lang, "back_btn"), callback_data=f"cat:{cat_id}:{page}"))
    return m


def _home_text(user, chat_id, lang):
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    display = f"@{user.username}" if user.username else name.strip() or str(user.id)
    return (
        f"{ui(lang, 'welcome', name=display)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ui(lang, 'user_id')} <code>{user.id}</code>\n"
        f"{ui(lang, 'chat_id')} <code>{chat_id}</code>\n"
        f"{ui(lang, 'uname')} {name.strip() or display}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ui(lang, 'pick_cat')}"
    )


# ── Handler registration ──────────────────────────────────────────────────────

def register(bot, custom_command_handler, command_prefixes_list, check_usage_limit=None):

    @custom_command_handler("start")
    @custom_command_handler("arise")
    async def start_command(message):
        from handlers.share_handler import handle_deep_link
        if await handle_deep_link(bot, message):
            return

        user = message.from_user
        if not has_lang_set(user.id):
            await bot.send_message(
                message.chat.id,
                _UI["en"]["lang_prompt"],
                reply_markup=_lang_select_markup(),
            )
            return

        lang = get_lang(user.id)
        await bot.send_message(
            message.chat.id,
            _home_text(user, message.chat.id, lang),
            reply_markup=_home_markup(lang),
        )

    @custom_command_handler("lang")
    async def lang_command(message):
        lang = get_lang(message.from_user.id)
        await bot.send_message(
            message.chat.id,
            ui(lang, "change_lang"),
            reply_markup=_lang_select_markup(),
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("lang_select:"))
    async def cb_lang_select(call):
        chosen = call.data.split(":")[1]
        set_lang(call.from_user.id, chosen)
        confirm_key = "lang_set_bn" if chosen == "bn" else "lang_set_en"
        lang = chosen

        text = (
            f"{ui(lang, confirm_key)}\n\n"
            + _home_text(call.from_user, call.message.chat.id, lang)
        )
        await bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=_home_markup(lang),
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "change_lang")
    async def cb_change_lang(call):
        lang = get_lang(call.from_user.id)
        await bot.edit_message_text(
            ui(lang, "change_lang"),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=_lang_select_markup(),
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "home")
    async def cb_home(call):
        lang = get_lang(call.from_user.id)
        await bot.edit_message_text(
            _home_text(call.from_user, call.message.chat.id, lang),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=_home_markup(lang),
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cat:"))
    async def cb_category(call):
        _, cat_id, page_str = call.data.split(":")
        page = int(page_str)
        if cat_id not in _CAT_MAP:
            await bot.answer_callback_query(call.id, "Unknown category")
            return

        lang = get_lang(call.from_user.id)
        cat = _CAT_MAP[cat_id]
        markup, page, total_pages = _category_markup(cat_id, page, lang)

        page_info = (f" <i>({ui(lang, 'page', cur=page+1, total=total_pages)})</i>"
                     if total_pages > 1 else "")
        text = f"{cat['name'][lang]}\n━━━━━━━━━━━━━━━━━━━━━━\n{ui(lang, 'pick_cmd')}{page_info}:"

        await bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
        )
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cmd:"))
    async def cb_command(call):
        parts = call.data.split(":")
        cat_id, cmd_idx = parts[1], int(parts[2])
        if cat_id not in _CAT_MAP:
            await bot.answer_callback_query(call.id, "Unknown command")
            return

        cat = _CAT_MAP[cat_id]
        if cmd_idx >= len(cat["cmds"]):
            await bot.answer_callback_query(call.id, "Command not found")
            return

        lang = get_lang(call.from_user.id)
        usage_text = cat["cmds"][cmd_idx]["text"][lang]
        markup = _cmd_markup(cat_id, cmd_idx, lang)

        await bot.edit_message_text(
            usage_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
        )
        await bot.answer_callback_query(call.id)
