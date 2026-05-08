import asyncio
import logging
from io import BytesIO
from datetime import datetime
from typing import List, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ChatType, ParseMode
import aiohttp
from PIL import Image, ImageDraw, ImageFont

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- JSON.bin Config ----------
JSONBIN_BIN_ID = "69fcb1edc0954111d8ee7ea5"
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_BASE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
JSONBIN_HEADERS = {"X-Access-Key": JSONBIN_ACCESS_KEY, "Content-Type": "application/json"}

BOT_TOKEN = "8796667551:AAFkP5STUqnsV7v0FtVrwnmmBZMJy7U8aaA"
DEVELOPER_ID = 8194390770
BOT_USERNAME = "@welcome_notify_bot"

BROADCAST_MSG = 1

# ---------- 4 Language Welcome Pack ----------
LANG = {
    "en": {
        "flag": "🇬🇧 English",
        "banner_text": "✨ Welcome {user} ✨",
        "welcome_caption": (
            "🌟 <b>Welcome to {group} Chat</b> 🌟\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🏷 <b>Name:</b> {name}\n"
            "🆔 <b>User ID:</b> <code>{uid}</code>\n"
            "🔗 <b>Username:</b> @{uname}\n"
            "👋 <b>Mention:</b> {mention}\n"
            "⏰ <b>Joined at:</b> <code>{time}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📢 <b>Follow Rules & Enjoy!</b>"
        ),
        "join_btn": "📢 Join Channel",
        "must_join": "❌ You must join {channel} to send messages in this group.",
        "set_usage": "Usage: /set https://t.me/yourchannel\nExample: /set https://t.me/smm_24_io",
        "set_success": "✅ Force channel added: {channel}",
        "set_fail": "❌ I'm not admin in {channel}. Please add me as admin first!\n\n1️⃣ Open {channel}\n2️⃣ Go to Settings → Administrators\n3️⃣ Add @{bot_username} as admin",
        "lang_ok": "✅ Language changed to English.",
        "choose_lang": "🌐 Choose bot language:",
        "start_priv": (
            "🤖 <b>Welcome Notify Bot</b>\n\n"
            "🔹 <b>Developer:</b> @bot_developer_io\n"
            "🔹 <b>Helper:</b> @jhgmaing\n\n"
            "📌 <b>Features:</b>\n"
            "• Custom Welcome Banner\n"
            "• Force Channel Support\n"
            "• Multi-Language\n"
            "• Broadcast System\n\n"
            "Add me to your group/channel!"
        ),
        "add_btn": "➕ Add me to your group/channel",
        "settings": "⚙️ Group Settings",
        "set_ch_btn": "📌 Set Force Channel",
        "lang_btn": "🌐 Language",
        "back": "🔙 Back"
    },
    "bn": {
        "flag": "🇧🇩 বাংলা",
        "banner_text": "✨ স্বাগতম {user} ✨",
        "welcome_caption": (
            "🌟 <b>{group} চ্যাটে স্বাগতম</b> 🌟\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🏷 <b>নাম:</b> {name}\n"
            "🆔 <b>ইউজার আইডি:</b> <code>{uid}</code>\n"
            "🔗 <b>ইউজারনেম:</b> @{uname}\n"
            "👋 <b>মেনশন:</b> {mention}\n"
            "⏰ <b>জয়েন টাইম:</b> <code>{time}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📢 <b>নিয়ম মেনে চলুন ও উপভোগ করুন!</b>"
        ),
        "join_btn": "📢 চ্যানেলে যুক্ত হন",
        "must_join": "❌ এই গ্রুপে মেসেজ পাঠাতে {channel} চ্যানেলে যোগ দিন।",
        "set_usage": "ব্যবহার: /set https://t.me/yourchannel\nউদাহরণ: /set https://t.me/smm_24_io",
        "set_success": "✅ ফোর্স চ্যানেল সেট হয়েছে: {channel}",
        "set_fail": "❌ আমি {channel} চ্যানেলের অ্যাডমিন নই। দয়া করে অ্যাডমিন বানান!\n\n1️⃣ {channel} ওপেন করুন\n2️⃣ Settings → Administrators এ যান\n3️⃣ @{bot_username} কে অ্যাডমিন বানান",
        "lang_ok": "✅ বাংলা ভাষা সেট করা হয়েছে।",
        "choose_lang": "🌐 বটের ভাষা নির্বাচন করুন:",
        "start_priv": (
            "🤖 <b>ওয়েলকাম নোটিফাই বট</b>\n\n"
            "🔹 <b>ডেভেলপার:</b> @bot_developer_io\n"
            "🔹 <b>হেল্পার:</b> @jhgmaing\n\n"
            "📌 <b>ফিচারস:</b>\n"
            "• কাস্টম ওয়েলকাম ব্যানার\n"
            "• ফোর্স চ্যানেল সাপোর্ট\n"
            "• মাল্টি-ল্যাঙ্গুয়েজ\n"
            "• ব্রডকাস্ট সিস্টেম\n\n"
            "গ্রুপ/চ্যানেলে যুক্ত করুন!"
        ),
        "add_btn": "➕ গ্রুপ/চ্যানেলে যোগ করুন",
        "settings": "⚙️ গ্রুপ সেটিংস",
        "set_ch_btn": "📌 ফোর্স চ্যানেল সেট",
        "lang_btn": "🌐 ভাষা",
        "back": "🔙 ফিরুন"
    },
    "ru": {
        "flag": "🇷🇺 Русский",
        "banner_text": "✨ Добро пожаловать {user} ✨",
        "welcome_caption": (
            "🌟 <b>Добро пожаловать в {group} Чат</b> 🌟\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🏷 <b>Имя:</b> {name}\n"
            "🆔 <b>ID:</b> <code>{uid}</code>\n"
            "🔗 <b>Юзернейм:</b> @{uname}\n"
            "👋 <b>Упоминание:</b> {mention}\n"
            "⏰ <b>Присоединился:</b> <code>{time}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📢 <b>Соблюдайте правила!</b>"
        ),
        "join_btn": "📢 Присоединиться",
        "must_join": "❌ Для отправки сообщений присоединитесь к {channel}.",
        "set_usage": "Использование: /set https://t.me/yourchannel\nПример: /set https://t.me/smm_24_io",
        "set_success": "✅ Канал добавлен: {channel}",
        "set_fail": "❌ Я не админ в {channel}. Сначала добавьте меня!\n\n1️⃣ Откройте {channel}\n2️⃣ Settings → Administrators\n3️⃣ Добавьте @{bot_username} как админа",
        "lang_ok": "✅ Язык изменён на русский.",
        "choose_lang": "🌐 Выберите язык:",
        "start_priv": (
            "🤖 <b>Welcome Notify Bot</b>\n\n"
            "🔹 <b>Разработчик:</b> @bot_developer_io\n"
            "🔹 <b>Помощник:</b> @jhgmaing\n\n"
            "Добавьте в группу/канал!"
        ),
        "add_btn": "➕ Добавить в группу/канал",
        "settings": "⚙️ Настройки",
        "set_ch_btn": "📌 Обязательный канал",
        "lang_btn": "🌐 Язык",
        "back": "🔙 Назад"
    },
    "hi": {
        "flag": "🇮🇳 हिन्दी",
        "banner_text": "✨ सुस्वागतम् {user} ✨",
        "welcome_caption": (
            "🌟 <b>{group} चैट में स्वागत</b> 🌟\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🏷 <b>नाम:</b> {name}\n"
            "🆔 <b>आईडी:</b> <code>{uid}</code>\n"
            "🔗 <b>यूजरनेम:</b> @{uname}\n"
            "👋 <b>उल्लेख:</b> {mention}\n"
            "⏰ <b>जॉइन समय:</b> <code>{time}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📢 <b>नियमों का पालन करें!</b>"
        ),
        "join_btn": "📢 चैनल से जुड़ें",
        "must_join": "❌ मैसेज करने के लिए {channel} जॉइन करें।",
        "set_usage": "उपयोग: /set https://t.me/yourchannel\nउदाहरण: /set https://t.me/smm_24_io",
        "set_success": "✅ चैनल सेट: {channel}",
        "set_fail": "❌ मैं {channel} का एडमिन नहीं। पहले जोड़ें!\n\n1️⃣ {channel} खोलें\n2️⃣ Settings → Administrators पर जाएं\n3️⃣ @{bot_username} को एडमिन बनाएं",
        "lang_ok": "✅ भाषा हिन्दी सेट।",
        "choose_lang": "🌐 भाषा चुनें:",
        "start_priv": (
            "🤖 <b>वेलकम नोटिफाई बॉट</b>\n\n"
            "🔹 <b>डेवलपर:</b> @bot_developer_io\n"
            "🔹 <b>हेल्पर:</b> @jhgmaing\n\n"
            "ग्रुप/चैनल में जोड़ें!"
        ),
        "add_btn": "➕ ग्रुप/चैनल में जोड़ें",
        "settings": "⚙️ सेटिंग्स",
        "set_ch_btn": "📌 फोर्स चैनल",
        "lang_btn": "🌐 भाषा",
        "back": "🔙 वापस"
    }
}

# ---------- Database Functions ----------
async def get_data(session) -> dict:
    try:
        async with session.get(f"{JSONBIN_BASE_URL}/latest", headers=JSONBIN_HEADERS) as r:
            if r.status == 200:
                return (await r.json()).get("record", {})
    except Exception as e:
        logger.error(f"DB get error: {e}")
    return {}

async def save_data(session, data: dict) -> bool:
    try:
        async with session.put(JSONBIN_BASE_URL, json=data, headers=JSONBIN_HEADERS) as r:
            return r.status == 200
    except Exception as e:
        logger.error(f"DB save error: {e}")
        return False

async def get_lang(chat_id: int, session) -> str:
    data = await get_data(session)
    return data.get("groups", {}).get(str(chat_id), {}).get("lang", "en")

async def set_lang(chat_id: int, lang: str, session):
    data = await get_data(session)
    data.setdefault("groups", {}).setdefault(str(chat_id), {})["lang"] = lang
    await save_data(session, data)

async def get_channels(chat_id: int, session) -> List[str]:
    data = await get_data(session)
    return data.get("groups", {}).get(str(chat_id), {}).get("forced_channels", [])

async def add_channel(chat_id: int, channel: str, session):
    data = await get_data(session)
    grp = data.setdefault("groups", {}).setdefault(str(chat_id), {"lang": "en", "forced_channels": []})
    channels = grp.setdefault("forced_channels", [])
    if channel not in channels:
        channels.append(channel)
        await save_data(session, data)

async def add_broadcast_id(cid: int, session):
    data = await get_data(session)
    ids = data.setdefault("broadcast_ids", [])
    if cid not in ids:
        ids.append(cid)
        await save_data(session, data)

async def get_broadcast_ids(session) -> List[int]:
    data = await get_data(session)
    return data.get("broadcast_ids", [])

# ---------- Image Generation ----------
def create_welcome_banner(group_photo: Optional[BytesIO], user_photo: Optional[BytesIO],
                          group_name: str, user_name: str, lang_code: str) -> BytesIO:
    width, height = 800, 400
    img = Image.new("RGB", (width, height), (23, 33, 43))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for i in range(height):
        ratio = i / height
        r = int(23 + (55 - 23) * ratio)
        g = int(33 + (65 - 33) * ratio)
        b = int(43 + (81 - 43) * ratio)
        draw.line((0, i, width, i), fill=(r, g, b))

    try:
        font_welcome = ImageFont.truetype("arial.ttf", 40)
        font_title = ImageFont.truetype("arial.ttf", 28)
    except:
        font_welcome = ImageFont.load_default()
        font_title = ImageFont.load_default()

    # Place group photo (circle) left
    if group_photo:
        try:
            g_img = Image.open(group_photo).convert("RGBA").resize((130, 130))
        except:
            g_img = Image.new("RGBA", (130, 130), (100, 100, 100))
    else:
        g_img = Image.new("RGBA", (130, 130), (100, 100, 100))
    mask = Image.new("L", (130, 130), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 129, 129), fill=255)
    g_img.putalpha(mask)
    img.paste(g_img, (70, 135), g_img)

    # Place user photo (circle) right
    if user_photo:
        try:
            u_img = Image.open(user_photo).convert("RGBA").resize((130, 130))
        except:
            u_img = Image.new("RGBA", (130, 130), (150, 150, 150))
    else:
        u_img = Image.new("RGBA", (130, 130), (150, 150, 150))
    u_img.putalpha(mask)
    img.paste(u_img, (600, 135), u_img)

    # Welcome text
    welcome_str = LANG.get(lang_code, LANG["en"])["banner_text"].format(user=user_name)
    bbox = draw.textbbox((0, 0), welcome_str, font=font_welcome)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 50), welcome_str, fill=(255, 255, 255), font=font_welcome)

    # Group name
    g_text = group_name[:30]
    gbox = draw.textbbox((0, 0), g_text, font=font_title)
    gw = gbox[2] - gbox[0]
    draw.text(((width - gw) // 2, 318), g_text, fill=(200, 200, 200), font=font_title)

    # User name
    u_text = user_name[:25]
    ubox = draw.textbbox((0, 0), u_text, font=font_title)
    uw = ubox[2] - ubox[0]
    draw.text(((width - uw) // 2, 355), u_text, fill=(200, 200, 200), font=font_title)

    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

# ---------- Photo Helpers ----------
async def get_photo_bytes(chat_or_user, bot) -> Optional[BytesIO]:
    try:
        if hasattr(chat_or_user, 'photo') and chat_or_user.photo:
            file_id = chat_or_user.photo.big_file_id
        else:
            photos = await chat_or_user.get_profile_photos(limit=1)
            if not photos.photos:
                return None
            file_id = photos.photos[0][-1].file_id
        file = await bot.get_file(file_id)
        bio = BytesIO()
        await file.download_to_memory(bio)
        bio.seek(0)
        return bio
    except:
        return None

async def get_group_photo_bytes(chat_id, bot) -> Optional[BytesIO]:
    try:
        chat = await bot.get_chat(chat_id)
        if chat.photo:
            return await get_photo_bytes(chat, bot)
    except:
        pass
    return None

# ---------- 🔧 FIXED: Channel Admin Check ----------
async def check_bot_is_admin(channel_id: str, bot) -> bool:
    """Check if bot is admin in the channel - 3 different methods"""
    
    # Method 1: Direct get_chat_member
    try:
        bot_member = await bot.get_chat_member(channel_id, bot.id)
        if bot_member.status in ['administrator', 'creator']:
            logger.info(f"✅ Method 1: Bot is {bot_member.status} in {channel_id}")
            return True
    except Exception as e1:
        logger.warning(f"Method 1 failed: {e1}")
    
    # Method 2: Get chat info and check
    try:
        chat = await bot.get_chat(channel_id)
        if chat.type in ['channel', 'supergroup']:
            # If we can get chat info and it's a channel, try to get administrators
            admins = await chat.get_administrators()
            for admin in admins:
                if admin.user.id == bot.id:
                    logger.info(f"✅ Method 2: Bot found in admin list of {channel_id}")
                    return True
    except Exception as e2:
        logger.warning(f"Method 2 failed: {e2}")
    
    # Method 3: Try sending a test message (last resort)
    try:
        test_msg = await bot.send_message(channel_id, "🔍 Admin check...", disable_notification=True)
        await test_msg.delete()
        logger.info(f"✅ Method 3: Bot can send messages in {channel_id} (must be admin)")
        return True
    except Exception as e3:
        logger.warning(f"Method 3 failed: {e3}")
    
    logger.error(f"❌ Bot is NOT admin in {channel_id}")
    return False

async def is_member(channel_id: str, user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ---------- 🔧 FIXED: /set command ----------
async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """One-step /set command: /set https://t.me/smm_24_io"""
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await update.message.reply_text("This command only works in groups.")
        return

    # Admin check
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        mem = await context.bot.get_chat_member(chat_id, user_id)
        if mem.status not in ('administrator', 'creator'):
            await update.message.reply_text("Only admins can use this command.")
            return
    except:
        return

    session = context.application.bot_data["session"]
    lang = await get_lang(chat_id, session)

    # Get channel from command argument
    if not context.args:
        await update.message.reply_text(LANG[lang]["set_usage"])
        return

    channel_text = context.args[0].strip()

    # Validate format
    if not (channel_text.startswith("@") or "t.me/" in channel_text or "telegram.me/" in channel_text):
        await update.message.reply_text(LANG[lang]["set_usage"])
        return

    # Send checking message
    checking_msg = await update.message.reply_text(f"🔍 Checking bot admin status in {channel_text}...")

    # 🔧 FIX: Use new admin check method
    is_admin = await check_bot_is_admin(channel_text, context.bot)
    
    # Delete checking message
    try:
        await checking_msg.delete()
    except:
        pass

    if not is_admin:
        await update.message.reply_text(
            LANG[lang]["set_fail"].format(channel=channel_text, bot_username=context.bot.username),
            disable_web_page_preview=True
        )
        return

    # Add to DB
    await add_channel(chat_id, channel_text, session)
    await update.message.reply_text(LANG[lang]["set_success"].format(channel=channel_text))

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.message
    session = context.application.bot_data["session"]
    if chat.type == ChatType.PRIVATE:
        await msg.reply_text(
            LANG["en"]["start_priv"],
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(LANG["en"]["add_btn"], url=f"https://t.me/{BOT_USERNAME[1:]}?startgroup=true")
            ]])
        )
        await add_broadcast_id(chat.id, session)
    else:
        user_id = update.effective_user.id
        try:
            mem = await context.bot.get_chat_member(chat.id, user_id)
            if mem.status not in ('administrator', 'creator'):
                return
        except:
            return
        lang = await get_lang(chat.id, session)
        btns = [
            [InlineKeyboardButton(LANG[lang]["set_ch_btn"], callback_data="set_force_channel")],
            [InlineKeyboardButton(LANG[lang]["lang_btn"], callback_data="change_lang")]
        ]
        await msg.reply_text(LANG[lang]["settings"], reply_markup=InlineKeyboardMarkup(btns))

# Broadcast
async def broadcast_start(update: Update, context):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("Unauthorized.")
        return ConversationHandler.END
    await update.message.reply_text("Send the message to broadcast.")
    return BROADCAST_MSG

async def broadcast_msg(update: Update, context):
    if update.effective_user.id != DEVELOPER_ID:
        return ConversationHandler.END
    msg = update.message
    ids = await get_broadcast_ids(context.application.bot_data["session"])
    sent = 0
    for cid in ids:
        try:
            await msg.copy(chat_id=cid)
            sent += 1
        except: pass
    await msg.reply_text(f"Broadcast sent to {sent}/{len(ids)} chats.")
    return ConversationHandler.END

broadcast_conv = ConversationHandler(
    entry_points=[CommandHandler("broadcast", broadcast_start)],
    states={BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_msg)]},
    fallbacks=[]
)

# Callbacks
async def callback_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    session = context.application.bot_data["session"]

    if data.startswith("setlang_"):
        lang = data.split("_")[1]
        await set_lang(chat_id, lang, session)
        await query.edit_message_text(LANG[lang]["lang_ok"])
    elif data == "change_lang":
        cur = await get_lang(chat_id, session)
        btns = [[InlineKeyboardButton(LANG[code]["flag"], callback_data=f"setlang_{code}")] for code in LANG]
        btns.append([InlineKeyboardButton(LANG[cur]["back"], callback_data="back_settings")])
        await query.edit_message_text(LANG[cur]["choose_lang"], reply_markup=InlineKeyboardMarkup(btns))
    elif data == "set_force_channel":
        cur = await get_lang(chat_id, session)
        await query.edit_message_text(f"Use /set command:\n{LANG[cur]['set_usage']}")
    elif data == "back_settings":
        cur = await get_lang(chat_id, session)
        btns = [
            [InlineKeyboardButton(LANG[cur]["set_ch_btn"], callback_data="set_force_channel")],
            [InlineKeyboardButton(LANG[cur]["lang_btn"], callback_data="change_lang")]
        ]
        await query.edit_message_text(LANG[cur]["settings"], reply_markup=InlineKeyboardMarkup(btns))

# 🌟🔥 PRO WELCOME - EVERY USER GETS WELCOME 🔥🌟
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    bot = context.bot
    session = context.application.bot_data["session"]
    lang = await get_lang(chat.id, session)

    for member in update.message.new_chat_members:
        if member.id == bot.id:
            continue

        logger.info(f"🎉 Welcoming {member.full_name} (ID: {member.id}) to {chat.title}")

        full_name = member.full_name or member.first_name or "User"
        user_id = member.id
        username = member.username or "N/A"
        mention = member.mention_html()
        join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        group_photo = await get_group_photo_bytes(chat.id, bot)
        user_photo = await get_photo_bytes(member, bot)

        try:
            banner = create_welcome_banner(group_photo, user_photo, chat.title, full_name, lang)
        except Exception as e:
            logger.error(f"Banner creation failed: {e}")
            banner = None

        caption = LANG[lang]["welcome_caption"].format(
            group=chat.title,
            name=full_name,
            uid=user_id,
            uname=username,
            mention=mention,
            time=join_time
        )

        channels = await get_channels(chat.id, session)
        markup = None
        if channels:
            btns = []
            for ch in channels:
                url = f"https://t.me/{ch[1:]}" if ch.startswith("@") else ch
                btns.append([InlineKeyboardButton(LANG[lang]["join_btn"], url=url)])
            markup = InlineKeyboardMarkup(btns)

        try:
            if banner:
                await bot.send_photo(chat.id, banner, caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
                banner.close()
                logger.info(f"✅ Welcome banner sent for {full_name}")
            else:
                await bot.send_message(chat.id, caption, parse_mode=ParseMode.HTML, reply_markup=markup)
                logger.info(f"✅ Text welcome sent for {full_name}")
        except Exception as e:
            logger.error(f"Failed to send welcome: {e}")
            try:
                await bot.send_message(chat.id, caption, parse_mode=ParseMode.HTML, reply_markup=markup)
            except: pass

# Force channel enforcement
async def message_filter(update: Update, context):
    if not update.message or update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return
    user = update.effective_user
    chat = update.effective_chat
    bot = context.bot
    session = context.application.bot_data["session"]
    channels = await get_channels(chat.id, session)
    if not channels:
        return
    try:
        mem = await bot.get_chat_member(chat.id, user.id)
        if mem.status in ('administrator', 'creator'):
            return
    except: pass
    missing = [ch for ch in channels if not await is_member(ch, user.id, bot)]
    if missing:
        try:
            await update.message.delete()
            lang = await get_lang(chat.id, session)
            warn = LANG[lang]["must_join"].format(channel="\n".join(missing))
            sent = await bot.send_message(chat.id, warn, parse_mode=ParseMode.HTML)
            await asyncio.sleep(5)
            await sent.delete()
        except: pass

# Track groups for broadcast
async def track_chat(update: Update, context):
    if update.my_chat_member and update.my_chat_member.new_chat_member.status in ('member', 'administrator'):
        await add_broadcast_id(update.effective_chat.id, context.application.bot_data["session"])
        logger.info(f"📝 Added to broadcast list: {update.effective_chat.id}")

# ---------- Session lifecycle ----------
async def post_init(application: Application):
    application.bot_data["session"] = aiohttp.ClientSession()
    session = application.bot_data["session"]
    data = await get_data(session)
    if not data:
        await save_data(session, {"groups": {}, "broadcast_ids": []})
        logger.info("✅ Initialized fresh JSON.bin")

async def post_shutdown(application: Application):
    session = application.bot_data.get("session")
    if session:
        await session.close()
        logger.info("🛑 Session closed")

# ---------- Main ----------
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("set", set_channel))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(broadcast_conv)
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(setlang_|change_lang|set_force_channel|back_settings)"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_filter), group=1)
    app.add_handler(ChatMemberHandler(track_chat, ChatMemberHandler.MY_CHAT_MEMBER))

    logger.info("🔥 Welcome Notify Bot is LIVE!")
    app.run_polling()

if __name__ == "__main__":
    main()
