import asyncio
import logging
from io import BytesIO
from typing import List, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes
)
from telegram.constants import ChatType, ParseMode
import aiohttp

# ---------- Logging ----------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- JSON.bin Configuration ----------
JSONBIN_BIN_ID = "69fcb1edc0954111d8ee7ea5"
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_BASE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
JSONBIN_HEADERS = {"X-Access-Key": JSONBIN_ACCESS_KEY, "Content-Type": "application/json"}

BOT_TOKEN = "8796667551:AAFkP5STUqnsV7v0FtVrwnmmBZMJy7U8aaA"
DEVELOPER_ID = 8194390770
BOT_USERNAME = "@welcome_notify_bot"

SET_CHANNEL_LINK, BROADCAST_MSG = range(2)

# ---------- Languages ----------
LANG = {
    "en": {
        "flag": "🇬🇧 English",
        "welcome": "🎉 Welcome to {group}, {user}!",
        "join_btn": "📢 Join Channel",
        "must_join": "❌ You must join {channel} to send messages.",
        "set_prompt": "Send channel link/username to force join.",
        "set_success": "✅ Force channel added.",
        "set_fail": "❌ I'm not admin in that channel. Add me as admin first.",
        "lang_ok": "✅ Language set to English.",
        "choose_lang": "Choose bot language:",
        "start_priv": (
            "🤖 <b>Welcome Notify Bot</b>\n\n"
            "<b>Developer:</b> @bot_developer_io\n"
            "<b>Helper:</b> @jhgmaing\n\n"
            "Add me to your group/channel."
        ),
        "add_btn": "➕ Add me to your group/channel",
        "settings": "⚙️ Group Settings",
        "set_ch_btn": "📌 Set Force Channel",
        "lang_btn": "🌐 Language",
        "back": "🔙 Back"
    },
    "bn": {
        "flag": "🇧🇩 বাংলা",
        "welcome": "🎉 {group} গ্রুপে স্বাগতম, {user}!",
        "join_btn": "📢 চ্যানেলে যুক্ত হন",
        "must_join": "❌ মেসেজ পাঠাতে {channel} চ্যানেলে যোগ দিন।",
        "set_prompt": "ফোর্স চ্যানেলের লিংক/ইউজারনেম দিন।",
        "set_success": "✅ ফোর্স চ্যানেল সেট হয়েছে।",
        "set_fail": "❌ আমি সেই চ্যানেলের অ্যাডমিন নই। আগে অ্যাডমিন বানান।",
        "lang_ok": "✅ বাংলা ভাষা সেট করা হয়েছে।",
        "choose_lang": "ভাষা নির্বাচন করুন:",
        "start_priv": (
            "🤖 <b>ওয়েলকাম নোটিফাই বট</b>\n\n"
            "ডেভেলপার: @bot_developer_io\n"
            "হেল্পার: @jhgmaing"
        ),
        "add_btn": "➕ গ্রুপ/চ্যানেলে যোগ করুন",
        "settings": "⚙️ গ্রুপ সেটিংস",
        "set_ch_btn": "📌 ফোর্স চ্যানেল সেট",
        "lang_btn": "🌐 ভাষা",
        "back": "🔙 ফিরুন"
    },
    "ru": {
        "flag": "🇷🇺 Русский",
        "welcome": "🎉 Добро пожаловать в {group}, {user}!",
        "join_btn": "📢 Присоединиться",
        "must_join": "❌ Для сообщений нужно быть в {channel}.",
        "set_prompt": "Отправьте ссылку/username канала.",
        "set_success": "✅ Канал добавлен.",
        "set_fail": "❌ Я не админ в этом канале.",
        "lang_ok": "✅ Язык: Русский.",
        "choose_lang": "Выберите язык:",
        "start_priv": "🤖 <b>Welcome Notify Bot</b>\n\nРазработчик: @bot_developer_io",
        "add_btn": "➕ Добавить в группу/канал",
        "settings": "⚙️ Настройки",
        "set_ch_btn": "📌 Обязательный канал",
        "lang_btn": "🌐 Язык",
        "back": "🔙 Назад"
    },
    "hi": {
        "flag": "🇮🇳 हिन्दी",
        "welcome": "🎉 {group} में स्वागत है, {user}!",
        "join_btn": "📢 चैनल से जुड़ें",
        "must_join": "❌ मैसेज के लिए {channel} जॉइन करें।",
        "set_prompt": "फोर्स चैनल का लिंक/यूजरनेम भेजें।",
        "set_success": "✅ चैनल सेट हो गया।",
        "set_fail": "❌ मैं उस चैनल का एडमिन नहीं।",
        "lang_ok": "✅ भाषा हिन्दी सेट।",
        "choose_lang": "भाषा चुनें:",
        "start_priv": "🤖 <b>वेलकम नोटिफाई बॉट</b>\n\nडेवलपर: @bot_developer_io",
        "add_btn": "➕ ग्रुप/चैनल में जोड़ें",
        "settings": "⚙️ सेटिंग्स",
        "set_ch_btn": "📌 फोर्स चैनल",
        "lang_btn": "🌐 भाषा",
        "back": "🔙 वापस"
    }
}

# ---------- Database Helpers ----------
async def get_data(session) -> dict:
    try:
        async with session.get(JSONBIN_BASE_URL + "/latest", headers=JSONBIN_HEADERS) as resp:
            if resp.status == 200:
                return (await resp.json()).get("record", {})
    except Exception as e:
        logger.error(f"DB get error: {e}")
    return {}

async def save_data(session, data: dict) -> bool:
    try:
        async with session.put(JSONBIN_BASE_URL, json=data, headers=JSONBIN_HEADERS) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"DB save error: {e}")
        return False

async def get_lang(chat_id: int, session) -> str:
    d = await get_data(session)
    return d.get("groups", {}).get(str(chat_id), {}).get("lang", "en")

async def set_lang(chat_id: int, lang: str, session):
    d = await get_data(session)
    d.setdefault("groups", {}).setdefault(str(chat_id), {})["lang"] = lang
    await save_data(session, d)

async def get_channels(chat_id: int, session) -> List[str]:
    d = await get_data(session)
    return d.get("groups", {}).get(str(chat_id), {}).get("forced_channels", [])

async def add_channel(chat_id: int, channel: str, session):
    d = await get_data(session)
    group = d.setdefault("groups", {}).setdefault(str(chat_id), {"lang": "en", "forced_channels": []})
    ch_list = group.setdefault("forced_channels", [])
    if channel not in ch_list:
        ch_list.append(channel)
        await save_data(session, d)

async def add_broadcast_id(cid: int, session):
    d = await get_data(session)
    ids = d.setdefault("broadcast_ids", [])
    if cid not in ids:
        ids.append(cid)
        await save_data(session, d)

async def get_broadcast_ids(session) -> List[int]:
    d = await get_data(session)
    return d.get("broadcast_ids", [])

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
    except Exception as e:
        logger.warning(f"Could not fetch photo: {e}")
        return None

async def get_group_photo_bytes(chat_id, bot) -> Optional[BytesIO]:
    try:
        chat = await bot.get_chat(chat_id)
        if chat.photo:
            return await get_photo_bytes(chat, bot)
    except Exception as e:
        logger.warning(f"Group photo error: {e}")
    return None

async def is_member(channel_id: str, user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    msg = update.message
    session = context.application.bot_data["session"]
    if chat.type == ChatType.PRIVATE:
        text = LANG["en"]["start_priv"]
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton(LANG["en"]["add_btn"], url=f"https://t.me/{BOT_USERNAME[1:]}?startgroup=true")]
        ])
        await msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=btn)
        await add_broadcast_id(chat.id, session)
    else:
        # Group admin panel
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

# /set conversation
async def set_ch_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return ConversationHandler.END
    user_id = update.effective_user.id
    try:
        mem = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        if mem.status not in ('administrator', 'creator'):
            await update.message.reply_text("Only admins can use this command.")
            return ConversationHandler.END
    except:
        return ConversationHandler.END
    lang = await get_lang(update.effective_chat.id, context.application.bot_data["session"])
    await update.message.reply_text(LANG[lang]["set_prompt"])
    return SET_CHANNEL_LINK

async def set_ch_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    session = context.application.bot_data["session"]
    lang = await get_lang(chat_id, session)

    if text.startswith("@") or "t.me/" in text:
        ch_id = text
    else:
        await update.message.reply_text("Invalid format. Use @username or invite link.")
        return ConversationHandler.END

    try:
        bot_member = await context.bot.get_chat_member(ch_id, context.bot.id)
        if bot_member.status not in ('administrator', 'creator'):
            raise Exception
    except:
        await update.message.reply_text(LANG[lang]["set_fail"])
        return ConversationHandler.END

    await add_channel(chat_id, ch_id, session)
    await update.message.reply_text(LANG[lang]["set_success"])
    return ConversationHandler.END

set_conv = ConversationHandler(
    entry_points=[CommandHandler("set", set_ch_start)],
    states={SET_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_ch_receive)]},
    fallbacks=[]
)

# Broadcast (Developer only)
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
        except:
            pass
    await msg.reply_text(f"Broadcast sent to {sent}/{len(ids)} chats.")
    return ConversationHandler.END

broadcast_conv = ConversationHandler(
    entry_points=[CommandHandler("broadcast", broadcast_start)],
    states={BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_msg)]},
    fallbacks=[]
)

# Callback handler for inline buttons
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
        lang_cur = await get_lang(chat_id, session)
        btns = [[InlineKeyboardButton(LANG[code]["flag"], callback_data=f"setlang_{code}")] for code in LANG]
        btns.append([InlineKeyboardButton(LANG[lang_cur]["back"], callback_data="back_settings")])
        await query.edit_message_text(LANG[lang_cur]["choose_lang"], reply_markup=InlineKeyboardMarkup(btns))
    elif data == "set_force_channel":
        lang_cur = await get_lang(chat_id, session)
        await query.edit_message_text(f"Use /set command to add a channel.\n{LANG[lang_cur]['set_prompt']}")
    elif data == "back_settings":
        lang_cur = await get_lang(chat_id, session)
        btns = [
            [InlineKeyboardButton(LANG[lang_cur]["set_ch_btn"], callback_data="set_force_channel")],
            [InlineKeyboardButton(LANG[lang_cur]["lang_btn"], callback_data="change_lang")]
        ]
        await query.edit_message_text(LANG[lang_cur]["settings"], reply_markup=InlineKeyboardMarkup(btns))

# 🌟 WELCOME HANDLER — THE HEART OF THE BOT 🌟
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    bot = context.bot
    session = context.application.bot_data["session"]
    lang = await get_lang(chat.id, session)

    for member in update.message.new_chat_members:
        # বট নিজে জয়েন করলে কিছু করবে না
        if member.id == bot.id:
            continue

        logger.info(f"New member {member.full_name} joined {chat.title}")
        try:
            group_photo = await get_group_photo_bytes(chat.id, bot)
            user_photo = await get_photo_bytes(member, bot)

            # Build media group
            media = []
            if group_photo:
                media.append(InputMediaPhoto(media=group_photo))
            if user_photo:
                media.append(InputMediaPhoto(media=user_photo))

            caption = LANG[lang]["welcome"].format(
                group=chat.title,
                user=member.mention_html()
            )

            # If we have at least one photo, send album
            if media:
                # Add caption and reply markup to last media
                media[-1].caption = caption
                media[-1].parse_mode = ParseMode.HTML

                # Force channel buttons (if any)
                channels = await get_channels(chat.id, session)
                if channels:
                    btns = []
                    for ch in channels:
                        url = f"https://t.me/{ch[1:]}" if ch.startswith("@") else ch
                        btns.append([InlineKeyboardButton(LANG[lang]["join_btn"], url=url)])
                    media[-1].reply_markup = InlineKeyboardMarkup(btns)

                await bot.send_media_group(chat_id=chat.id, media=media)
                logger.info(f"Welcome album sent for {member.full_name}")
            else:
                # No photo available → send text only
                channels = await get_channels(chat.id, session)
                markup = None
                if channels:
                    btns = []
                    for ch in channels:
                        url = f"https://t.me/{ch[1:]}" if ch.startswith("@") else ch
                        btns.append([InlineKeyboardButton(LANG[lang]["join_btn"], url=url)])
                    markup = InlineKeyboardMarkup(btns)

                await bot.send_message(
                    chat.id,
                    caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup
                )
                logger.info(f"Text-only welcome sent for {member.full_name}")

        except Exception as e:
            logger.error(f"Welcome handler error for {member.full_name}: {e}", exc_info=True)
            # Fallback: সরাসরি টেক্সট ওয়েলকাম দিবে কোনো ছবি ছাড়া
            try:
                fallback_text = LANG[lang]["welcome"].format(group=chat.title, user=member.mention_html())
                await bot.send_message(chat.id, fallback_text, parse_mode=ParseMode.HTML)
            except:
                pass

        finally:
            # Cleanup BytesIO objects
            if 'group_photo' in locals() and group_photo:
                group_photo.close()
            if 'user_photo' in locals() and user_photo:
                user_photo.close()

# Force channel enforcement
async def message_filter(update: Update, context):
    if not update.message or update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    user = update.effective_user
    chat = update.effective_chat
    bot = context.bot
    session = context.application.bot_data["session"]
    channels = await get_channels(chat.id, session)
    if not channels:
        return

    # Admin/moderator should bypass
    try:
        mem = await bot.get_chat_member(chat.id, user.id)
        if mem.status in ('administrator', 'creator'):
            return
    except:
        pass

    missing = [ch for ch in channels if not await is_member(ch, user.id, bot)]
    if missing:
        try:
            await update.message.delete()
            lang = await get_lang(chat.id, session)
            warn = LANG[lang]["must_join"].format(channel="\n".join(missing))
            sent = await bot.send_message(chat.id, warn, parse_mode=ParseMode.HTML)
            await asyncio.sleep(5)
            await sent.delete()
        except Exception as e:
            logger.error(f"Force-channel error: {e}")

# Track chats for broadcast
async def track_chat(update: Update, context):
    if update.my_chat_member and update.my_chat_member.new_chat_member.status in ('member', 'administrator'):
        await add_broadcast_id(update.effective_chat.id, context.application.bot_data["session"])
        logger.info(f"Bot added to chat {update.effective_chat.id}")

# ---------- Session lifecycle ----------
async def post_init(application: Application):
    application.bot_data["session"] = aiohttp.ClientSession()
    session = application.bot_data["session"]
    # Initialize DB if empty
    data = await get_data(session)
    if not data:
        await save_data(session, {"groups": {}, "broadcast_ids": []})
        logger.info("Initialized fresh JSON.bin")
    else:
        logger.info("JSON.bin loaded")

async def post_shutdown(application: Application):
    session = application.bot_data.get("session")
    if session:
        await session.close()
        logger.info("HTTP session closed")

# ---------- Main ----------
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(set_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(setlang_|change_lang|set_force_channel|back_settings)"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_filter), group=1)
    app.add_handler(ChatMemberHandler(track_chat, ChatMemberHandler.MY_CHAT_MEMBER))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
