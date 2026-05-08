import asyncio
import logging
import os
from io import BytesIO
from typing import List, Dict, Any, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ChatPermissions
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ChatMemberHandler, filters, ContextTypes
)
from telegram.constants import ChatType, ParseMode
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------- JSON.bin Configuration ----------
JSONBIN_BIN_ID = "69fcb1edc0954111d8ee7ea5"
JSONBIN_ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_BASE_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
JSONBIN_HEADERS = {"X-Access-Key": JSONBIN_ACCESS_KEY, "Content-Type": "application/json"}

# ---------- Bot Config ----------
BOT_TOKEN = "8796667551:AAFkP5STUqnsV7v0FtVrwnmmBZMJy7U8aaA"
DEVELOPER_ID = 8194390770
BOT_USERNAME = "@welcome_notify_bot"

# ---------- Conversation states ----------
SET_CHANNEL_LINK, BROADCAST_MSG = range(2)

# ---------- Languages dictionary ----------
LANGUAGES = {
    "en": {
        "flag": "🇬🇧 English",
        "welcome_text": "Welcome to {group}, {user}!",
        "banner_text": "Welcome {user}",
        "join_channel": "📢 Join Channel",
        "must_join_warn": "You must join {channel} to send messages in this group.",
        "set_channel_prompt": "Please send the channel link or username you want to force join.",
        "set_success": "✅ Force channel added successfully.",
        "set_fail_no_admin": "❌ I am not an admin in that channel. Please add me as admin first.",
        "lang_changed": "✅ Language changed to English.",
        "choose_lang": "Choose bot language:",
        "start_private": (
            "🤖 <b>Welcome to Welcome Notify Bot!</b>\n\n"
            "I can welcome new members with a custom banner, manage forced channels, and more!\n\n"
            "🔹 <b>Developer:</b> @bot_developer_io\n"
            "🔹 <b>Helper:</b> @jhgmaing\n\n"
            "Use the button below to add me to your group or channel."
        ),
        "add_button": "➕ Add me to your group / channel",
        "settings_menu": "⚙️ Group Settings",
        "set_channel_btn": "📌 Set Force Channel",
        "change_lang_btn": "🌐 Change Language",
        "back": "🔙 Back"
    },
    "bn": {
        "flag": "🇧🇩 বাংলা",
        "welcome_text": "{group} গ্রুপে স্বাগতম, {user}!",
        "banner_text": "স্বাগতম {user}",
        "join_channel": "📢 চ্যানেলে যোগ দিন",
        "must_join_warn": "এই গ্রুপে মেসেজ পাঠাতে আপনাকে {channel} চ্যানেলে যোগ দিতে হবে।",
        "set_channel_prompt": "অনুগ্রহ করে ফোর্স জয়েনের জন্য চ্যানেলের লিংক বা ইউজারনেম পাঠান।",
        "set_success": "✅ ফোর্স চ্যানেল সফলভাবে যোগ করা হয়েছে।",
        "set_fail_no_admin": "❌ আমি সেই চ্যানেলের অ্যাডমিন নই। দয়া করে আগে আমাকে অ্যাডমিন বানান।",
        "lang_changed": "✅ ভাষা বাংলায় পরিবর্তন করা হয়েছে।",
        "choose_lang": "বটের ভাষা বাছাই করুন:",
        "start_private": (
            "🤖 <b>ওয়েলকাম নোটিফাই বটে স্বাগতম!</b>\n\n"
            "আমি কাস্টম ব্যানার দিয়ে নতুন সদস্যদের স্বাগত জানাই, ফোর্স চ্যানেল ম্যানেজ করি এবং আরও অনেক কিছু!\n\n"
            "🔹 <b>ডেভেলপার:</b> @bot_developer_io\n"
            "🔹 <b>হেল্পার:</b> @jhgmaing\n\n"
            "নিচের বাটন ব্যবহার করে আমাকে আপনার গ্রুপ বা চ্যানেলে যুক্ত করুন।"
        ),
        "add_button": "➕ গ্রুপ / চ্যানেলে যুক্ত করুন",
        "settings_menu": "⚙️ গ্রুপ সেটিংস",
        "set_channel_btn": "📌 ফোর্স চ্যানেল সেট",
        "change_lang_btn": "🌐 ভাষা পরিবর্তন",
        "back": "🔙 ফিরে যান"
    },
    "ru": {
        "flag": "🇷🇺 Русский",
        "welcome_text": "Добро пожаловать в {group}, {user}!",
        "banner_text": "Добро пожаловать {user}",
        "join_channel": "📢 Присоединиться к каналу",
        "must_join_warn": "Вы должны присоединиться к {channel}, чтобы отправлять сообщения в этой группе.",
        "set_channel_prompt": "Пожалуйста, отправьте ссылку или имя канала для принудительного вступления.",
        "set_success": "✅ Канал принудительного вступления успешно добавлен.",
        "set_fail_no_admin": "❌ Я не администратор в этом канале. Сначала добавьте меня в админы.",
        "lang_changed": "✅ Язык изменён на русский.",
        "choose_lang": "Выберите язык бота:",
        "start_private": (
            "🤖 <b>Добро пожаловать в Welcome Notify Bot!</b>\n\n"
            "Я могу приветствовать новых участников с кастомным баннером, управлять обязательными каналами и многое другое!\n\n"
            "🔹 <b>Разработчик:</b> @bot_developer_io\n"
            "🔹 <b>Помощник:</b> @jhgmaing\n\n"
            "Нажмите на кнопку ниже, чтобы добавить меня в группу или канал."
        ),
        "add_button": "➕ Добавить в группу / канал",
        "settings_menu": "⚙️ Настройки группы",
        "set_channel_btn": "📌 Установить обязательный канал",
        "change_lang_btn": "🌐 Сменить язык",
        "back": "🔙 Назад"
    },
    "hi": {
        "flag": "🇮🇳 हिन्दी",
        "welcome_text": "{group} में आपका स्वागत है, {user}!",
        "banner_text": "स्वागत है {user}",
        "join_channel": "📢 चैनल से जुड़ें",
        "must_join_warn": "इस ग्रुप में संदेश भेजने के लिए आपको {channel} से जुड़ना होगा।",
        "set_channel_prompt": "कृपया फोर्स जॉइन के लिए चैनल का लिंक या यूजरनेम भेजें।",
        "set_success": "✅ फोर्स चैनल सफलतापूर्वक जोड़ा गया।",
        "set_fail_no_admin": "❌ मैं उस चैनल का एडमिन नहीं हूँ। पहले मुझे एडमिन बनाएँ।",
        "lang_changed": "✅ भाषा हिन्दी में बदल दी गई।",
        "choose_lang": "बॉट की भाषा चुनें:",
        "start_private": (
            "🤖 <b>वेलकम नोटिफाई बॉट में आपका स्वागत है!</b>\n\n"
            "मैं नए सदस्यों का कस्टम बैनर से स्वागत करता हूँ, फोर्स चैनल प्रबंधित करता हूँ और बहुत कुछ!\n\n"
            "🔹 <b>डेवलपर:</b> @bot_developer_io\n"
            "🔹 <b>सहायक:</b> @jhgmaing\n\n"
            "मुझे अपने ग्रुप या चैनल में जोड़ने के लिए नीचे दिए गए बटन का उपयोग करें।"
        ),
        "add_button": "➕ ग्रुप / चैनल में जोड़ें",
        "settings_menu": "⚙️ ग्रुप सेटिंग्स",
        "set_channel_btn": "📌 फोर्स चैनल सेट करें",
        "change_lang_btn": "🌐 भाषा बदलें",
        "back": "🔙 वापस"
    }
}

# ---------- Default Lang ----------
DEFAULT_LANG = "en"

# ---------- Database functions ----------
async def get_bin_data(session: aiohttp.ClientSession) -> dict:
    try:
        async with session.get(JSONBIN_BASE_URL + "/latest", headers=JSONBIN_HEADERS) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("record", {})
            else:
                logging.error(f"Failed to fetch bin: {resp.status}")
                return {}
    except Exception as e:
        logging.error(f"Error fetching bin: {e}")
        return {}

async def save_bin_data(session: aiohttp.ClientSession, data: dict) -> bool:
    try:
        async with session.put(JSONBIN_BASE_URL, json=data, headers=JSONBIN_HEADERS) as resp:
            return resp.status == 200
    except Exception as e:
        logging.error(f"Error saving bin: {e}")
        return False

async def get_group_lang(chat_id: int, session: aiohttp.ClientSession) -> str:
    data = await get_bin_data(session)
    return data.get("groups", {}).get(str(chat_id), {}).get("lang", DEFAULT_LANG)

async def set_group_lang(chat_id: int, lang: str, session: aiohttp.ClientSession):
    data = await get_bin_data(session)
    if "groups" not in data:
        data["groups"] = {}
    if str(chat_id) not in data["groups"]:
        data["groups"][str(chat_id)] = {"lang": DEFAULT_LANG, "forced_channels": []}
    data["groups"][str(chat_id)]["lang"] = lang
    await save_bin_data(session, data)

async def get_forced_channels(chat_id: int, session: aiohttp.ClientSession) -> List[str]:
    data = await get_bin_data(session)
    group_data = data.get("groups", {}).get(str(chat_id), {})
    return group_data.get("forced_channels", [])

async def add_forced_channel(chat_id: int, channel_identifier: str, session: aiohttp.ClientSession):
    data = await get_bin_data(session)
    if "groups" not in data:
        data["groups"] = {}
    if str(chat_id) not in data["groups"]:
        data["groups"][str(chat_id)] = {"lang": DEFAULT_LANG, "forced_channels": []}
    channels: list = data["groups"][str(chat_id)].setdefault("forced_channels", [])
    if channel_identifier not in channels:
        channels.append(channel_identifier)
        await save_bin_data(session, data)

async def remove_forced_channel(chat_id: int, channel_identifier: str, session: aiohttp.ClientSession):
    data = await get_bin_data(session)
    group_data = data.get("groups", {}).get(str(chat_id))
    if group_data and channel_identifier in group_data.get("forced_channels", []):
        group_data["forced_channels"].remove(channel_identifier)
        await save_bin_data(session, data)

async def add_broadcast_ids(chat_id: int, session: aiohttp.ClientSession):
    data = await get_bin_data(session)
    if "broadcast_ids" not in data:
        data["broadcast_ids"] = []
    if chat_id not in data["broadcast_ids"]:
        data["broadcast_ids"].append(chat_id)
        await save_bin_data(session, data)

async def get_all_broadcast_ids(session: aiohttp.ClientSession) -> List[int]:
    data = await get_bin_data(session)
    return data.get("broadcast_ids", [])

# ---------- Helper: Image generation ----------
async def create_welcome_banner(group_photo_bytes: Optional[bytes],
                                user_photo_bytes: Optional[bytes],
                                group_name: str, user_name: str, lang: str) -> BytesIO:
    # Create 800x400 banner
    width, height = 800, 400
    bg_color = (23, 33, 43)  # Dark blue-grey
    gradient_top = (55, 65, 81)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Simple gradient background (vertical)
    for i in range(height):
        ratio = i / height
        r = int(bg_color[0] + (gradient_top[0]-bg_color[0])*ratio)
        g = int(bg_color[1] + (gradient_top[1]-bg_color[1])*ratio)
        b = int(bg_color[2] + (gradient_top[2]-bg_color[2])*ratio)
        draw.line((0, i, width, i), fill=(r, g, b))

    # Fonts (using default PIL font if system font not available)
    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 28)
        font_welcome = ImageFont.truetype("arial.ttf", 50)
    except:
        font_title = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_welcome = ImageFont.load_default()

    # Place group logo (circle) on the left
    group_logo = None
    if group_photo_bytes:
        try:
            group_logo = Image.open(BytesIO(group_photo_bytes)).convert("RGBA")
        except:
            pass
    if group_logo is None:
        group_logo = Image.new("RGBA", (150, 150), (100, 100, 100))
        draw_logo = ImageDraw.Draw(group_logo)
        draw_logo.ellipse((0,0,149,149), fill=(120,120,120))
    group_logo = group_logo.resize((150, 150))
    # Create circular mask
    mask = Image.new("L", (150, 150), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0,0,149,149), fill=255)
    group_logo.putalpha(mask)
    img.paste(group_logo, (80, 125), group_logo)

    # Place user photo (circle) on the right
    user_photo = None
    if user_photo_bytes:
        try:
            user_photo = Image.open(BytesIO(user_photo_bytes)).convert("RGBA")
        except:
            pass
    if user_photo is None:
        user_photo = Image.new("RGBA", (150, 150), (150, 150, 150))
        draw_user = ImageDraw.Draw(user_photo)
        draw_user.ellipse((0,0,149,149), fill=(180,180,180))
    user_photo = user_photo.resize((150, 150))
    user_photo.putalpha(mask)
    img.paste(user_photo, (570, 125), user_photo)

    # Welcome text
    welcome_msg = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANG])["banner_text"].format(user=user_name)
    # Center the main text
    text_bbox = draw.textbbox((0,0), welcome_msg, font=font_welcome)
    text_w = text_bbox[2]-text_bbox[0]
    draw.text((width/2 - text_w/2, 60), welcome_msg, fill=(255, 255, 255), font=font_welcome)

    # Group name
    group_text = group_name[:30]  # truncate
    gbbox = draw.textbbox((0,0), group_text, font=font_title)
    gw = gbbox[2]-gbbox[0]
    draw.text((width/2 - gw/2, 320), group_text, fill=(200, 200, 200), font=font_title)

    # User name
    user_text = user_name[:25]
    ubbox = draw.textbbox((0,0), user_text, font=font_small)
    uw = ubbox[2]-ubbox[0]
    draw.text((width/2 - uw/2, 360), user_text, fill=(200, 200, 200), font=font_small)

    # Convert to bytes
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output

async def get_file_bytes(photo_sizes, bot) -> Optional[bytes]:
    """Download the largest photo size and return bytes."""
    if not photo_sizes:
        return None
    file_id = photo_sizes[-1].file_id
    file = await bot.get_file(file_id)
    bytes_io = BytesIO()
    await file.download_to_memory(bytes_io)
    return bytes_io.getvalue()

async def get_chat_photo_bytes(chat_id, bot) -> Optional[bytes]:
    """Get chat photo bytes, may fail if no photo or bot not admin."""
    try:
        chat = await bot.get_chat(chat_id)
        if chat.photo:
            return await get_file_bytes([chat.photo], bot)
    except:
        pass
    return None

# ---------- Check forced channel membership ----------
async def is_user_member_of_channel(user_id: int, channel_identifier: str, bot) -> bool:
    """Check if user is member of channel (public/private). Returns True if member, False otherwise.
    For private channels, bot must be admin and identifier can be invite link or chat id."""
    try:
        # Try to get chat member with user_id
        member = await bot.get_chat_member(chat_id=channel_identifier, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        # Not a member or invalid channel
        pass
    return False

async def delete_message_and_warn(update: Update, context, missing_channels: List[str]):
    """Delete the message and send a warning about missing channels."""
    try:
        await update.message.delete()
        # Send a warning that auto-deletes after 5s
        channel_links = "\n".join(missing_channels)
        warn_msg = LANGUAGES.get(context.chat_data.get("lang", DEFAULT_LANG), LANGUAGES[DEFAULT_LANG]) \
                        ["must_join_warn"].format(channel=channel_links)
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=warn_msg,
            parse_mode=ParseMode.HTML
        )
        # Delete the warning after 5 seconds
        await asyncio.sleep(5)
        await sent_msg.delete()
    except Exception as e:
        logging.error(f"Error in force-ch message handling: {e}")

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message in private with add button."""
    if update.effective_chat.type == ChatType.PRIVATE:
        lang = DEFAULT_LANG  # private default language
        text = LANGUAGES[lang]["start_private"]
        add_button = InlineKeyboardButton(
            text=LANGUAGES[lang]["add_button"],
            url=f"https://t.me/{BOT_USERNAME[1:]}?startgroup=true"
        )
        reply_markup = InlineKeyboardMarkup([[add_button]])
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    else:
        # In group, show settings panel (admin only)
        chat_id = update.effective_chat.id
        session = context.application.bot_data.get("aiohttp_session")
        lang = await get_group_lang(chat_id, session)
        if await is_group_admin(update, context):
            buttons = [
                [InlineKeyboardButton(text=LANGUAGES[lang]["set_channel_btn"], callback_data="set_force_channel")],
                [InlineKeyboardButton(text=LANGUAGES[lang]["change_lang_btn"], callback_data="change_lang")],
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text(
                LANGUAGES[lang]["settings_menu"],
                reply_markup=reply_markup
            )
        else:
            # Normal members don't get menu
            pass

async def is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin in the group."""
    if update.effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            return member.status in ('administrator', 'creator')
        except:
            pass
    return False

# Conversation for /set command (force channel)
async def set_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /set - prompts for channel link."""
    if not await is_group_admin(update, context):
        await update.message.reply_text("Only admins can use this command.")
        return ConversationHandler.END
    session = context.application.bot_data.get("aiohttp_session")
    lang = await get_group_lang(update.effective_chat.id, session)
    await update.message.reply_text(LANGUAGES[lang]["set_channel_prompt"])
    return SET_CHANNEL_LINK

async def set_channel_receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the channel link and add to forced list."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()
    session = context.application.bot_data.get("aiohttp_session")
    lang = await get_group_lang(chat_id, session)

    # Extract channel identifier (username or invite link)
    channel_id = None
    if text.startswith("@"):
        channel_id = text  # public username
    elif "t.me/" in text or "telegram.me/" in text:
        # For invite links, we need to verify bot is admin
        # Use the link directly as identifier
        channel_id = text
    else:
        await update.message.reply_text("Invalid format. Please send a username like @channel or an invite link.")
        return ConversationHandler.END

    # Verify bot is admin in that channel
    try:
        # Check if bot can get itself as admin
        bot_member = await context.bot.get_chat_member(chat_id=channel_id, user_id=context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            raise Exception("Not admin")
    except:
        await update.message.reply_text(LANGUAGES[lang]["set_fail_no_admin"])
        return ConversationHandler.END

    # Add to database
    await add_forced_channel(chat_id, channel_id, session)
    await update.message.reply_text(LANGUAGES[lang]["set_success"])
    return ConversationHandler.END

set_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("set", set_channel_start)],
    states={
        SET_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_channel_receive_link)]
    },
    fallbacks=[],
)

# Broadcast conversation (developer only)
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("You are not authorized.")
        return ConversationHandler.END
    await update.message.reply_text("Send the message you want to broadcast to all groups/users.")
    return BROADCAST_MSG

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        return ConversationHandler.END
    message = update.message
    session = context.application.bot_data.get("aiohttp_session")
    broadcast_ids = await get_all_broadcast_ids(session)
    success = 0
    for cid in broadcast_ids:
        try:
            await message.copy(chat_id=cid)
            success += 1
        except:
            pass
    await update.message.reply_text(f"Broadcast sent to {success}/{len(broadcast_ids)} chats.")
    return ConversationHandler.END

broadcast_conv = ConversationHandler(
    entry_points=[CommandHandler("broadcast", broadcast_start)],
    states={
        BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)]
    },
    fallbacks=[],
)

# Language change via callback
async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("setlang_"):
        lang = data.split("_")[1]
        chat_id = update.effective_chat.id
        session = context.application.bot_data.get("aiohttp_session")
        await set_group_lang(chat_id, lang, session)
        await query.edit_message_text(
            text=LANGUAGES[lang]["lang_changed"]
        )
    elif data == "change_lang":
        # Show language selection
        session = context.application.bot_data.get("aiohttp_session")
        current_lang = await get_group_lang(update.effective_chat.id, session)
        buttons = []
        for code, info in LANGUAGES.items():
            buttons.append([InlineKeyboardButton(text=info["flag"], callback_data=f"setlang_{code}")])
        buttons.append([InlineKeyboardButton(text=LANGUAGES[current_lang]["back"], callback_data="back_settings")])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(
            text=LANGUAGES[current_lang]["choose_lang"],
            reply_markup=reply_markup
        )
    elif data == "set_force_channel":
        # Redirect to /set command? Actually we can prompt like conversation
        # For simplicity, we tell user to use /set command or cancel.
        lang = await get_group_lang(update.effective_chat.id, context.application.bot_data.get("aiohttp_session"))
        await query.edit_message_text(
            text=f"Use /set command to add a force channel. {LANGUAGES[lang]['set_channel_prompt']}"
        )
    elif data == "back_settings":
        # Return to main settings
        lang = await get_group_lang(update.effective_chat.id, context.application.bot_data.get("aiohttp_session"))
        buttons = [
            [InlineKeyboardButton(text=LANGUAGES[lang]["set_channel_btn"], callback_data="set_force_channel")],
            [InlineKeyboardButton(text=LANGUAGES[lang]["change_lang_btn"], callback_data="change_lang")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(LANGUAGES[lang]["settings_menu"], reply_markup=reply_markup)

# Welcome new members with banner
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when one or more new members join."""
    chat = update.effective_chat
    bot = context.bot
    session = context.application.bot_data.get("aiohttp_session")
    lang = await get_group_lang(chat.id, session)
    
    # Get group photo bytes
    group_photo_bytes = await get_chat_photo_bytes(chat.id, bot)
    
    for member in update.message.new_chat_members:
        # Ignore bot itself
        if member.id == bot.id:
            continue

        # Get user profile photo
        user_photo_bytes = None
        try:
            photos = await member.get_profile_photos(limit=1)
            if photos.photos:
                user_photo_bytes = await get_file_bytes(photos.photos[0], bot)
        except:
            pass
        
        # Create banner
        banner_io = await create_welcome_banner(
            group_photo_bytes=group_photo_bytes,
            user_photo_bytes=user_photo_bytes,
            group_name=chat.title or "Group",
            user_name=member.full_name or member.first_name or "User",
            lang=lang
        )

        # Build keyboard with forced channels
        forced_channels = await get_forced_channels(chat.id, session)
        keyboard = []
        for ch in forced_channels:
            # Create join button with link
            if ch.startswith("@"):
                url = f"https://t.me/{ch[1:]}"
            else:
                url = ch  # invite link
            keyboard.append([InlineKeyboardButton(text=LANGUAGES[lang]["join_channel"], url=url)])
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        caption = LANGUAGES[lang]["welcome_text"].format(group=chat.title, user=member.mention_html())
        await bot.send_photo(
            chat_id=chat.id,
            photo=banner_io,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        banner_io.close()

# Auto-delete messages from users not in forced channels
async def check_forced_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is member of all forced channels and delete if not."""
    chat = update.effective_chat
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    user = update.effective_user
    if user.id == context.bot.id:
        return  # ignore bot
    session = context.application.bot_data.get("aiohttp_session")
    forced_channels = await get_forced_channels(chat.id, session)
    if not forced_channels:
        return

    # Check membership
    bot = context.bot
    missing = []
    for ch in forced_channels:
        if not await is_user_member_of_channel(user.id, ch, bot):
            missing.append(ch)
    if missing:
        await delete_message_and_warn(update, context, missing)

# Track groups for broadcast (when bot added to group)
async def track_chat_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When bot is added to a group, store its ID."""
    chat = update.effective_chat
    session = context.application.bot_data.get("aiohttp_session")
    await add_broadcast_ids(chat.id, session)

async def track_private_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Private start also stores user for broadcast."""
    if update.effective_chat.type == ChatType.PRIVATE:
        session = context.application.bot_data.get("aiohttp_session")
        await add_broadcast_ids(update.effective_chat.id, session)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")

# ---------- Main ----------
async def main():
    # Logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    # Build application
    app = Application.builder().token(BOT_TOKEN).build()

    # aiohttp session
    async with aiohttp.ClientSession() as session:
        app.bot_data["aiohttp_session"] = session

        # Initialize / ensure JSON bin has structure
        data = await get_bin_data(session)
        if not data:
            init_data = {"groups": {}, "broadcast_ids": []}
            await save_bin_data(session, init_data)

        # Handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(set_conv_handler)
        app.add_handler(broadcast_conv)
        app.add_handler(CallbackQueryHandler(lang_callback, pattern="^(setlang_|change_lang|set_force_channel|back_settings)"))
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_forced_channels))
        app.add_handler(ChatMemberHandler(track_chat_added, ChatMemberHandler.CHAT_MEMBER))
        app.add_handler(MessageHandler(filters.ALL, track_private_start))  # just for private tracking, but better to limit
        # Start bot
        await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
