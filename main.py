import asyncio
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler, ContextTypes
)
import aiohttp

# ==================== কনফিগারেশন ====================
BOT_TOKEN = "8760307687:AAG6sLpnxTZJtlqDuCgWzAzmui39HWmtsu0"
ADMIN_ID = 8194390770
CHANNEL_1 = "@earning_channel24"
CHANNEL_2 = "@smm_24_io"
CHANNELS = [CHANNEL_1, CHANNEL_2]
REFERRAL_BONUS = 0.3
MIN_WITHDRAW = 1.0
SUPPORT_USERNAME = "@bot_developer_io"

# JSON.bin
BIN_ID = "69fcb1edc0954111d8ee7ea5"
MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    "X-Master-Key": MASTER_KEY,
    "X-Access-Key": ACCESS_KEY,
    "Content-Type": "application/json"
}

# ==================== স্টেট (ConversationHandler) ====================
# Withdraw states
WITHDRAW_AMOUNT, WITHDRAW_PAYMENT = range(2)
# Broadcast
BROADCAST_MSG = 2
# Add balance
ADD_BAL_USER_ID, ADD_BAL_AMOUNT = range(2, 4)
# Cut balance
CUT_BAL_USER_ID, CUT_BAL_AMOUNT = range(4, 6)
# Ban
BAN_USER_ID = 6
# Unban
UNBAN_USER_ID = 7

# ==================== লগিং ====================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ডাটাবেজ হেল্পার ====================
data_lock = asyncio.Lock()

async def get_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(JSONBIN_URL, headers=HEADERS) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("record", {})
            return {}

async def save_data(data: dict):
    async with aiohttp.ClientSession() as session:
        async with session.put(JSONBIN_URL, headers=HEADERS, json=data) as resp:
            if resp.status == 200:
                logger.info("Data saved")
            else:
                logger.error(f"Save failed: {resp.status}")

async def get_user(user_id: int):
    data = await get_data()
    return data.get("users", {}).get(str(user_id), None)

async def update_user(user_id: int, user_data: dict):
    async with data_lock:
        data = await get_data()
        users = data.get("users", {})
        users[str(user_id)] = user_data
        data["users"] = users
        await save_data(data)

async def get_all_user_ids():
    data = await get_data()
    return list(data.get("users", {}).keys())

# ==================== চ্যানেল চেক ====================
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ==================== কিবোর্ড (বক্স বাটন) ====================
def main_menu_keyboard(is_admin=False):
    buttons = [
        ["💰 ব্যালেন্স", "👥 রেফারেল"],
        ["📤 উইথড্র", "📜 হিস্টোরি"],
        ["🆘 হেল্প"]
    ]
    if is_admin:
        buttons.append(["⚙️ অ্যাডমিন প্যানেল"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def admin_menu_keyboard():
    buttons = [
        ["📢 ব্রডকাস্ট", "💰 ব্যালেন্স যোগ"],
        ["💸 ব্যালেন্স কাট", "🚫 ব্যান ইউজার"],
        ["🔓 আনব্যান ইউজার", "📋 পেন্ডিং উইথড্র"],
        ["🔙 মেইন মেনু"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ==================== /start হ্যান্ডলার ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.full_name

    # ব্যান চেক
    usr = await get_user(user_id)
    if usr and usr.get("banned"):
        await update.message.reply_text("⛔ আপনি বট থেকে ব‍্যানড।")
        return

    # নতুন ইউজার তৈরি
    if not usr:
        await update_user(user_id, {
            "balance": 0.0,
            "referral_count": 0,
            "referred_by": None,
            "banned": False,
            "joined_channels": False,
            "referral_credited": False
        })

    # রেফারেল প্রক্রিয়া (ডিপ লিংক)
    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])
        if ref_id != user_id:
            usr = await get_user(user_id)
            if usr.get("referred_by") is None:
                usr["referred_by"] = ref_id
                await update_user(user_id, usr)
                # রেফারারকে নোটিফিকেশন
                try:
                    await context.bot.send_message(ref_id,
                        f"🔔 @{username} আপনার রেফারেল লিংক দিয়ে বট জয়েন করেছে।\n"
                        "চ্যানেল জয়েন করলে আপনি 0.03 টাকা পাবেন।")
                except:
                    pass

    # চ্যানেল মেম্বারশিপ চেক
    if await is_member(user_id, context):
        usr = await get_user(user_id)
        if not usr.get("joined_channels"):
            usr["joined_channels"] = True
            if usr.get("referred_by") and not usr.get("referral_credited"):
                ref_id = usr["referred_by"]
                ref_usr = await get_user(ref_id)
                if ref_usr:
                    ref_usr["balance"] = round(ref_usr.get("balance", 0.0) + REFERRAL_BONUS, 2)
                    ref_usr["referral_count"] = ref_usr.get("referral_count", 0) + 1
                    await update_user(ref_id, ref_usr)
                    await context.bot.send_message(ref_id,
                        f"🎉 আপনার রেফারেল @{username} চ্যানেল জয়েন করেছে! আপনি 0.03 টাকা পেয়েছেন।")
                usr["referral_credited"] = True
            await update_user(user_id, usr)
        # পূর্ণাঙ্গ মেনু পাঠাই
        await update.message.reply_text(
            f"╔══════════════════╗\n"
            f"<b>EARNING BY REFER24 💸</b>\n"
            f"╚══════════════════╝\n\n"
            f"👋 স্বাগতম, <b>{user.full_name}</b>!\n"
            f"────────────────────\n"
            f"📌 প্রতি রেফারেল = 0.03 টাকা\n"
            f"📌 উইথড্র মিনিমাম = 1 টাকা\n"
            f"📌 চ্যানেল জয়েন আবশ্যক\n"
            f"────────────────────\n"
            f"🆘 সাপোর্ট: {SUPPORT_USERNAME}",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(is_admin=(user_id == ADMIN_ID))
        )
    else:
        # জয়েন করানোর ইনলাইন বাটন (শুধু এখানে ইনলাইন)
        inline_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📣 Channel 1", url=f"https://t.me/{CHANNEL_1[1:]}"),
             InlineKeyboardButton("📣 Channel 2", url=f"https://t.me/{CHANNEL_2[1:]}")],
            [InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_join")]
        ])
        await update.message.reply_text(
            f"╔══════════════════╗\n"
            f"<b>EARNING BY REFER24 💸</b>\n"
            f"╚══════════════════╝\n\n"
            f"👋 স্বাগতম, <b>{user.full_name}</b>!\n"
            f"🔒 বট ইউজ করতে নিচের দুটি চ্যানেলে জয়েন করে \"জয়েন করেছি\" বাটনে ক্লিক করুন।",
            parse_mode="HTML",
            reply_markup=inline_kb
        )

# ==================== জয়েন চেক (ইনলাইন কলব্যাক) ====================
async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if await is_member(user_id, context):
        usr = await get_user(user_id)
        if not usr.get("joined_channels"):
            usr["joined_channels"] = True
            if usr.get("referred_by") and not usr.get("referral_credited"):
                ref_id = usr["referred_by"]
                ref_usr = await get_user(ref_id)
                if ref_usr:
                    ref_usr["balance"] = round(ref_usr.get("balance", 0.0) + REFERRAL_BONUS, 2)
                    ref_usr["referral_count"] = ref_usr.get("referral_count", 0) + 1
                    await update_user(ref_id, ref_usr)
                    try:
                        await context.bot.send_message(ref_id,
                            f"🎉 আপনার রেফারেল @{query.from_user.username or query.from_user.full_name} চ্যানেল জয়েন করেছে! আপনি 0.03 টাকা পেয়েছেন।")
                    except:
                        pass
                usr["referral_credited"] = True
            await update_user(user_id, usr)
        # পুরানো ইনলাইন মেসেজ মুছে দিয়ে কিবোর্ডমেনু পাঠাই
        await query.message.delete()
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ জয়েন সফল! এখন নিচের বাটন থেকে কাজ শুরু করুন।",
            reply_markup=main_menu_keyboard(is_admin=(user_id == ADMIN_ID))
        )
    else:
        await query.answer("❗ এখনো জয়েন করেননি! দুই চ্যানেলেই জয়েন করুন।", show_alert=True)

# ==================== মেনু বাটন হ্যান্ডলার (টেক্সট মেসেজ) ====================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if user and user.get("banned"):
        await update.message.reply_text("⛔ আপনি ব্যানড।")
        return
    if not await is_member(user_id, context):
        await update.message.reply_text("❗ দয়া করে @earning_channel24 এবং @smm_24_io চ্যানেলে জয়েন করুন।")
        return

    if text == "💰 ব্যালেন্স":
        bal = user.get("balance", 0.0)
        await update.message.reply_text(f"💳 আপনার ব্যালেন্স: <b>{bal} টাকা</b>", parse_mode="HTML")
    elif text == "👥 রেফারেল":
        link = f"https://t.me/earning_by_refer24_bot?start={user_id}"
        count = user.get("referral_count", 0)
        await update.message.reply_text(
            f"🔗 <b>তোমার রেফারেল লিংক:</b>\n<code>{link}</code>\n\n"
            f"👥 মোট রেফারেল: {count}\n"
            f"প্রতি রেফার = 0.03 টাকা",
            parse_mode="HTML"
        )
    elif text == "📤 উইথড্র":
        return await withdraw_start(update, context)
    elif text == "📜 হিস্টোরি":
        data = await get_data()
        my_requests = [r for r in data.get("withdrawals", []) if r["user_id"] == user_id]
        if not my_requests:
            await update.message.reply_text("📭 কোনো উইথড্র রিকোয়েস্ট নেই।")
        else:
            msg = "📜 <b>উইথড্র হিস্টোরি</b>\n"
            for r in my_requests[-5:]:
                emoji = "⏳" if r["status"]=="pending" else ("✅" if r["status"]=="approved" else "❌")
                msg += f"#{r['id']} | {r['amount']} টাকা | {emoji} {r['status']}\n"
            await update.message.reply_text(msg, parse_mode="HTML")
    elif text == "🆘 হেল্প":
        await update.message.reply_text(
            f"🆘 <b>Earning By Refer24 বট</b>\n\n"
            f"• রেফার করে আয় 0.03 টাকা\n"
            f"• উইথড্র মিনিমাম 1 টাকা\n"
            f"• জয়েন করতে হবে ২ চ্যানেল\n"
            f"• প্রশ্ন? সাপোর্ট: {SUPPORT_USERNAME}",
            parse_mode="HTML"
        )
    elif text == "⚙️ অ্যাডমিন প্যানেল" and user_id == ADMIN_ID:
        await update.message.reply_text("⚙️ অ্যাডমিন প্যানেল", reply_markup=admin_menu_keyboard())
    elif text == "🔙 মেইন মেনু" and user_id == ADMIN_ID:
        await update.message.reply_text("🔝 মেইন মেনু", reply_markup=main_menu_keyboard(is_admin=True))
    elif text == "📢 ব্রডকাস্ট" and user_id == ADMIN_ID:
        await update.message.reply_text("📢 সকল ইউজারকে যে মেসেজ পাঠাতে চান সেটি লিখুন (টেক্সট/ফটো/ভিডিও):", reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True))
        return BROADCAST_MSG
    elif text == "💰 ব্যালেন্স যোগ" and user_id == ADMIN_ID:
        await update.message.reply_text("➕ যার ব্যালেন্স যোগ করবেন তার ইউজার আইডি দিন:", reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True))
        return ADD_BAL_USER_ID
    elif text == "💸 ব্যালেন্স কাট" and user_id == ADMIN_ID:
        await update.message.reply_text("➖ যার ব্যালেন্স কাটবেন তার ইউজার আইডি দিন:", reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True))
        return CUT_BAL_USER_ID
    elif text == "🚫 ব্যান ইউজার" and user_id == ADMIN_ID:
        await update.message.reply_text("🚫 ব্যান করতে চান তার ইউজার আইডি দিন:", reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True))
        return BAN_USER_ID
    elif text == "🔓 আনব্যান ইউজার" and user_id == ADMIN_ID:
        await update.message.reply_text("🔓 আনব্যান করতে চান তার ইউজার আইডি দিন:", reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True))
        return UNBAN_USER_ID
    elif text == "📋 পেন্ডিং উইথড্র" and user_id == ADMIN_ID:
        data = await get_data()
        pending = [r for r in data.get("withdrawals", []) if r["status"] == "pending"]
        if not pending:
            await update.message.reply_text("কোনো পেন্ডিং রিকোয়েস্ট নেই।")
            return
        for req in pending:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"approve_{req['id']}"),
                 InlineKeyboardButton("❌ রিজেক্ট", callback_data=f"reject_{req['id']}")]
            ])
            await update.message.reply_text(
                f"🔔 #{req['id']} | @{req['username']} | {req['amount']} টাকা",
                reply_markup=kb
            )

# ==================== উইথড্র কনভারসেশন ====================
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if user["balance"] < MIN_WITHDRAW:
        await update.message.reply_text(f"❌ মিনিমাম {MIN_WITHDRAW} টাকা দরকার। আপনার ব্যালেন্স {user['balance']} টাকা।")
        return ConversationHandler.END
    await update.message.reply_text(
        f"💸 কত টাকা উইথড্র করতে চান? (আপনার ব্যালেন্স: {user['balance']} টাকা)\n"
        "টাইপ করুন পরিমাণ:",
        reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True)
    )
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ বাতিল":
        return await cancel_withdraw(update, context)
    try:
        amount = float(text)
    except:
        await update.message.reply_text("❗ সঠিক সংখ্যা লিখুন।")
        return WITHDRAW_AMOUNT
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if amount < MIN_WITHDRAW or amount > user["balance"]:
        await update.message.reply_text(f"❌ অকার্যকর পরিমাণ। আপনার ব্যালেন্স: {user['balance']} টাকা, মিনিমাম {MIN_WITHDRAW} টাকা।")
        return WITHDRAW_AMOUNT
    context.user_data["withdraw_amount"] = amount
    await update.message.reply_text(
        "📱 আপনার বিকাশ/নগদ পার্সোনাল নাম্বার লিখুন (11 ডিজিট):",
        reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True)
    )
    return WITHDRAW_PAYMENT

async def withdraw_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ বাতিল":
        return await cancel_withdraw(update, context)
    number = text.strip()
    if not number.isdigit() or len(number) != 11:
        await update.message.reply_text("❗ ভুল নাম্বার। 11 ডিজিটের মোবাইল নাম্বার দিন।")
        return WITHDRAW_PAYMENT
    user_id = update.effective_user.id
    amount = context.user_data["withdraw_amount"]
    user = await get_user(user_id)
    # রিকোয়েস্ট তৈরি
    data = await get_data()
    w_list = data.get("withdrawals", [])
    req_id = len(w_list) + 1
    req = {
        "id": req_id,
        "user_id": user_id,
        "username": update.effective_user.username or update.effective_user.full_name,
        "amount": amount,
        "number": number,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    w_list.append(req)
    data["withdrawals"] = w_list
    await save_data(data)
    # ব্যালেন্স থেকে কেটে নেওয়া (হোল্ড) - আসলে আমরা সাথে সাথে কাটব না, অ্যাডমিন এপ্রুভ করলে কাটব। 
    # কিন্তু ইউজারকে দেখাতে হবে যে রিকোয়েস্ট হয়েছে, ব্যালেন্স দেখাবে আগের মতোই।
    # তাই আমরা এখনই কাটছি না।
    # অ্যাডমিনকে জানানো
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"approve_{req_id}"),
         InlineKeyboardButton("❌ রিজেক্ট", callback_data=f"reject_{req_id}")]
    ])
    await context.bot.send_message(
        ADMIN_ID,
        f"🔔 <b>নতুন উইথড্র রিকোয়েস্ট</b> #{req_id}\n"
        f"👤 @{req['username']} (<code>{user_id}</code>)\n"
        f"💰 {amount} টাকা\n"
        f"📱 {number}",
        reply_markup=admin_kb,
        parse_mode="HTML"
    )
    # চ্যানেলে ইনভয়েস
    await context.bot.send_message(
        CHANNEL_2,
        f"🧾 <b>Invoice #INV{req_id}</b>\n"
        f"👤 User: @{req['username']}\n"
        f"💰 Amount: {amount} BDT\n"
        f"📱 Number: {number}\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Status: Pending",
        parse_mode="HTML"
    )
    await update.message.reply_text(
        f"✅ আপনার {amount} টাকার উইথড্র রিকোয়েস্ট জমা হয়েছে।\n"
        "অনুমোদন পেলে টাকা পাঠানো হবে।",
        reply_markup=main_menu_keyboard(is_admin=(user_id == ADMIN_ID))
    )
    return ConversationHandler.END

async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ উইথড্র বাতিল করা হয়েছে।", reply_markup=main_menu_keyboard(is_admin=(update.effective_user.id == ADMIN_ID)))
    return ConversationHandler.END

# ==================== অ্যাডমিন কনভারসেশন: ব্রডকাস্ট ====================
async def broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ বাতিল":
        await update.message.reply_text("বাতিল", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    user_ids = await get_all_user_ids()
    msg = update.message
    count = 0
    for uid in user_ids:
        try:
            await context.bot.copy_message(chat_id=int(uid), from_chat_id=msg.chat_id, message_id=msg.message_id)
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ ব্রডকাস্ট: {count}/{len(user_ids)} জন পেয়েছে।", reply_markup=admin_menu_keyboard())
    return ConversationHandler.END

# ==================== অ্যাডমিন: ব্যালেন্স যোগ ====================
async def add_bal_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ বাতিল":
        await update.message.reply_text("বাতিল", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    try:
        tid = int(update.message.text)
        context.user_data["target_id"] = tid
        await update.message.reply_text("💰 কত টাকা যোগ করবেন?", reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True))
        return ADD_BAL_AMOUNT
    except:
        await update.message.reply_text("❗ সঠিক ইউজার আইডি দিন।")
        return ADD_BAL_USER_ID

async def add_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ বাতিল":
        await update.message.reply_text("বাতিল", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    try:
        amount = float(update.message.text)
        tid = context.user_data["target_id"]
        usr = await get_user(tid)
        if not usr:
            await update.message.reply_text("ইউজার পাওয়া যায়নি।", reply_markup=admin_menu_keyboard())
            return ConversationHandler.END
        usr["balance"] = round(usr.get("balance", 0.0) + amount, 2)
        await update_user(tid, usr)
        await update.message.reply_text(f"✅ {tid} এর ব্যালেন্সে {amount} টাকা যোগ হয়েছে।", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    except:
        await update.message.reply_text("❗ সঠিক পরিমাণ দিন।")
        return ADD_BAL_AMOUNT

# ==================== ব্যালেন্স কাট ====================
async def cut_bal_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ বাতিল":
        await update.message.reply_text("বাতিল", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    try:
        tid = int(update.message.text)
        context.user_data["target_id"] = tid
        await update.message.reply_text("💸 কত টাকা কাটবেন?", reply_markup=ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True))
        return CUT_BAL_AMOUNT
    except:
        await update.message.reply_text("❗ সঠিক ইউজার আইডি দিন।")
        return CUT_BAL_USER_ID

async def cut_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ বাতিল":
        await update.message.reply_text("বাতিল", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    try:
        amount = float(update.message.text)
        tid = context.user_data["target_id"]
        usr = await get_user(tid)
        if not usr:
            await update.message.reply_text("ইউজার পাওয়া যায়নি।", reply_markup=admin_menu_keyboard())
            return ConversationHandler.END
        usr["balance"] = round(usr.get("balance", 0.0) - amount, 2)
        await update_user(tid, usr)
        await update.message.reply_text(f"✅ {tid} এর ব্যালেন্স থেকে {amount} টাকা কাটা হয়েছে।", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    except:
        await update.message.reply_text("❗ সঠিক পরিমাণ দিন।")
        return CUT_BAL_AMOUNT

# ==================== ব্যান ====================
async def ban_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ বাতিল":
        await update.message.reply_text("বাতিল", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    try:
        tid = int(update.message.text)
        usr = await get_user(tid)
        if not usr:
            await update.message.reply_text("ইউজার নেই।", reply_markup=admin_menu_keyboard())
        else:
            usr["banned"] = True
            await update_user(tid, usr)
            await update.message.reply_text(f"⛔ {tid} ব্যান করা হয়েছে।", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    except:
        await update.message.reply_text("❗ ভুল আইডি।")
        return BAN_USER_ID

# ==================== আনব্যান ====================
async def unban_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ বাতিল":
        await update.message.reply_text("বাতিল", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    try:
        tid = int(update.message.text)
        usr = await get_user(tid)
        if not usr:
            await update.message.reply_text("ইউজার নেই।", reply_markup=admin_menu_keyboard())
        else:
            usr["banned"] = False
            await update_user(tid, usr)
            await update.message.reply_text(f"✅ {tid} আনব্যান হয়েছে।", reply_markup=admin_menu_keyboard())
        return ConversationHandler.END
    except:
        await update.message.reply_text("❗ ভুল আইডি।")
        return UNBAN_USER_ID

# ==================== উইথড্র এপ্রুভ/রিজেক্ট (ইনলাইন) ====================
async def approve_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        await query.answer("অননুমোদিত", show_alert=True)
        return
    data = query.data
    action, req_id = data.split("_")
    req_id = int(req_id)
    db = await get_data()
    w_list = db.get("withdrawals", [])
    req = next((r for r in w_list if r["id"] == req_id and r["status"] == "pending"), None)
    if not req:
        await query.answer("রিকোয়েস্ট পাওয়া যায়নি।")
        return
    if action == "approve":
        # ব্যালেন্স চেক ও কাট
        usr = await get_user(req["user_id"])
        if usr and usr["balance"] >= req["amount"]:
            usr["balance"] = round(usr["balance"] - req["amount"], 2)
            await update_user(req["user_id"], usr)
            req["status"] = "approved"
            # ডাটা আপডেট
            w_list = [r if r["id"] != req_id else req for r in w_list]
            db["withdrawals"] = w_list
            await save_data(db)
            await context.bot.send_message(req["user_id"], f"✅ আপনার {req['amount']} টাকা উইথড্র এপ্রুভ হয়েছে।")
            await query.edit_message_text(f"✅ #{req_id} এপ্রুভ করা হয়েছে।")
            # চ্যানেলে ইনভয়েস আপডেট? ঐচ্ছিক
        else:
            req["status"] = "rejected"
            w_list = [r if r["id"] != req_id else req for r in w_list]
            db["withdrawals"] = w_list
            await save_data(db)
            await context.bot.send_message(req["user_id"], "❌ আপনার উইথড্র রিকোয়েস্ট রিজেক্ট হয়েছে (পর্যাপ্ত ব্যালেন্স নেই)।")
            await query.edit_message_text(f"❌ #{req_id} রিজেক্ট (ব্যালেন্স কম)।")
    else:  # reject
        req["status"] = "rejected"
        w_list = [r if r["id"] != req_id else req for r in w_list]
        db["withdrawals"] = w_list
        await save_data(db)
        await context.bot.send_message(req["user_id"], f"❌ আপনার {req['amount']} টাকা উইথড্র রিজেক্ট হয়েছে।")
        await query.edit_message_text(f"❌ #{req_id} রিজেক্ট করা হয়েছে।")

# ==================== মেইন ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # কমান্ড
    app.add_handler(CommandHandler("start", start))

    # জয়েন চেক কলব্যাক (ইনলাইন)
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="check_join"))
    # উইথড্র এপ্রুভ/রিজেক্ট কলব্যাক
    app.add_handler(CallbackQueryHandler(approve_reject_callback, pattern=r"^(approve|reject)_\d+$"))

    # উইথড্র কনভারসেশন (শুরু হবে "📤 উইথড্র" টেক্সটে)
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 উইথড্র$"), withdraw_start)],
        states={
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            WITHDRAW_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_payment)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ বাতিল$"), cancel_withdraw)],
    )
    app.add_handler(withdraw_conv)

    # অ্যাডমিন ব্রডকাস্ট কনভারসেশন
    broadcast_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 ব্রডকাস্ট$"), menu_handler)],  # menu_handler state return BROADCAST_MSG
        states={
            BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_msg)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ বাতিল$"), lambda u,c: ConversationHandler.END)],
    )
    app.add_handler(broadcast_conv)

    # ব্যালেন্স যোগ কনভ
    add_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💰 ব্যালেন্স যোগ$"), menu_handler)],
        states={
            ADD_BAL_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bal_user_id)],
            ADD_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bal_amount)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ বাতিল$"), lambda u,c: admin_menu_fallback(u,c))],
    )
    app.add_handler(add_bal_conv)

    # ব্যালেন্স কাট কনভ
    cut_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 ব্যালেন্স কাট$"), menu_handler)],
        states={
            CUT_BAL_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, cut_bal_user_id)],
            CUT_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cut_bal_amount)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ বাতিল$"), lambda u,c: admin_menu_fallback(u,c))],
    )
    app.add_handler(cut_bal_conv)

    # ব্যান
    ban_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🚫 ব্যান ইউজার$"), menu_handler)],
        states={BAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_user_id)]},
        fallbacks=[MessageHandler(filters.Regex("^❌ বাতিল$"), lambda u,c: admin_menu_fallback(u,c))],
    )
    app.add_handler(ban_conv)

    # আনব্যান
    unban_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔓 আনব্যান ইউজার$"), menu_handler)],
        states={UNBAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, unban_user_id)]},
        fallbacks=[MessageHandler(filters.Regex("^❌ বাতিল$"), lambda u,c: admin_menu_fallback(u,c))],
    )
    app.add_handler(unban_conv)

    # সাধারণ মেনু হ্যান্ডলার (সব কিবোর্ড বাটন যা আলাদা কনভারসেশন নয়)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    # ফলব্যাক (যাতে কিবোর্ডের বাইরে টেক্সট দিলে রিমাইন্ডার দেয়)
    async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❗ দয়া করে নিচের বাটন ব্যবহার করুন।")
    app.add_handler(MessageHandler(filters.ALL, unknown))

    app.run_polling(drop_pending_updates=True)

async def admin_menu_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ বাতিল", reply_markup=admin_menu_keyboard())
    return ConversationHandler.END

if __name__ == "__main__":
    main()
