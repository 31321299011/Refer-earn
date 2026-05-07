import asyncio
import json
import logging
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    constants
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
import aiohttp

# ========== সেটিংস ==========
BOT_TOKEN = "8760307687:AAG6sLpnxTZJtlqDuCgWzAzmui39HWmtsu0"
ADMIN_ID = 8194390770
CHANNELS = ["@earning_channel24", "@smm_24_io"]
REFERRAL_BONUS = 0.03
MIN_WITHDRAW = 1.0

# JSON.bin কনফিগারেশন
BIN_ID = "69fcb1edc0954111d8ee7ea5"
MASTER_KEY = "$2a$10$Q.jxca3Wg3HLncJRJeBsF.XceuKNM6RFay0f3JE7WpalVC/G7I5S."
ACCESS_KEY = "$2a$10$7Nb5QAYjDezYlvPsRMGxnerfh.nthYJtLF3ac54jCIucQUsS3y3Ya"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    "X-Master-Key": MASTER_KEY,
    "X-Access-Key": ACCESS_KEY,
    "Content-Type": "application/json"
}

# ========== কনভারসেশন স্টেট ==========
BROADCAST, ADD_BAL_USER, ADD_BAL_AMOUNT, CUT_BAL_USER, CUT_BAL_AMOUNT, BAN_USER, UNBAN_USER = range(7)

# ========== লগিং ==========
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ডাটা ম্যানেজার ==========
data_lock = asyncio.Lock()

async def get_data():
    """JSON.bin থেকে সম্পূর্ণ ডাটা পড়ে আনে"""
    async with aiohttp.ClientSession() as session:
        async with session.get(JSONBIN_URL, headers=HEADERS) as resp:
            if resp.status == 200:
                res = await resp.json()
                return res.get("record", {})
            else:
                logger.error(f"ডাটা পড়তে সমস্যা: {resp.status}")
                return {}

async def save_data(data: dict):
    """JSON.bin-এ সম্পূর্ণ ডাটা আপডেট করে"""
    async with aiohttp.ClientSession() as session:
        async with session.put(JSONBIN_URL, headers=HEADERS, json=data) as resp:
            if resp.status == 200:
                logger.info("ডাটা সেভ সম্পন্ন")
            else:
                logger.error(f"ডাটা সেভ ব্যর্থ: {resp.status}")

async def get_user(user_id: int):
    """একটি ইউজারের ডাটা রিটার্ন করে, না থাকলে None"""
    data = await get_data()
    users = data.get("users", {})
    return users.get(str(user_id), None)

async def update_user(user_id: int, user_data: dict):
    """একটি ইউজারের ডাটা আপডেট বা তৈরি করে"""
    async with data_lock:
        data = await get_data()
        users = data.get("users", {})
        users[str(user_id)] = user_data
        data["users"] = users
        await save_data(data)

async def get_all_users():
    """সব ইউজার আইডি লিস্ট"""
    data = await get_data()
    return list(data.get("users", {}).keys())

# ========== হেল্পার ==========
async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """ইউজার দুই চ্যানেলেই জয়েন করেছে কি না চেক করে"""
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ইউজার ব্যানড কিনা, আর চ্যানেল মেম্বার কিনা – ব্যর্থ হলে পপআপ দিয়ে রিটার্ন False"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if user and user.get("banned", False):
        await update.callback_query.answer("⛔ আপনি বট থেকে ব্যানড!", show_alert=True)
        return False
    if not await check_membership(user_id, context):
        await update.callback_query.answer(
            "❗ আপনাকে @earning_channel24 এবং @smm_24_io দুটি চ্যানেলেই জয়েন করতে হবে!",
            show_alert=True
        )
        return False
    return True

# ========== মেনু জেনারেটর ==========
def main_menu(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance")],
        [InlineKeyboardButton("👥 রেফারেল লিংক", callback_data="referral")],
        [InlineKeyboardButton("📤 উইথড্র", callback_data="withdraw")],
        [InlineKeyboardButton("📜 উইথড্র হিস্টোরি", callback_data="history")],
        [InlineKeyboardButton("🆘 হেল্প", callback_data="help")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ অ্যাডমিন প্যানেল", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def channel_join_keyboard():
    keyboard = [
        [InlineKeyboardButton("📣 Join Channel 1", url="https://t.me/earning_channel24")],
        [InlineKeyboardButton("📣 Join Channel 2", url="https://t.me/smm_24_io")],
        [InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

back_button = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরে যান", callback_data="back_main")]])

# ========== /start হ্যান্ডলার ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.full_name

    # ব্যান চেক
    user_data = await get_user(user_id)
    if user_data and user_data.get("banned", False):
        await update.message.reply_text("⛔ আপনি বট থেকে ব্যানড।")
        return

    # নতুন ইউজার এন্ট্রি
    if not user_data:
        await update_user(user_id, {
            "balance": 0.0,
            "referral_count": 0,
            "referred_by": None,
            "banned": False,
            "joined_channels": False,
            "referral_credited": False
        })

    # রেফারেল প্যারাম প্রসেসিং
    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])
        if ref_id != user_id:
            user_data = await get_user(user_id)
            if user_data.get("referred_by") is None:
                user_data["referred_by"] = ref_id
                await update_user(user_id, user_data)
                # রেফারারকে নোটিফাই
                ref_text = f"🔔 <b>@{username}</b> আপনার রেফারেল লিংক দিয়ে বট জয়েন করেছে!\n"
                ref_text += "👉 ও যদি উভয় চ্যানেলে জয়েন করে, তাহলে আপনি 0.03 টাকা পাবেন।"
                try:
                    await context.bot.send_message(chat_id=ref_id, text=ref_text, parse_mode="HTML")
                except:
                    pass

    # চ্যানেল চেক করে জয়েন স্ট্যাটাস আপডেট
    joined = await check_membership(user_id, context)
    if joined:
        user_data = await get_user(user_id)
        if not user_data.get("joined_channels", False):
            user_data["joined_channels"] = True
            # রেফারেল ক্রেডিট
            if user_data.get("referred_by") and not user_data.get("referral_credited", False):
                ref_id = user_data["referred_by"]
                ref_user = await get_user(ref_id)
                if ref_user:
                    ref_user["balance"] = round(ref_user.get("balance", 0.0) + REFERRAL_BONUS, 2)
                    ref_user["referral_count"] = ref_user.get("referral_count", 0) + 1
                    await update_user(ref_id, ref_user)
                    await context.bot.send_message(ref_id,
                        f"🎉 আপনার রেফারেল @{username} উভয় চ্যানেলে জয়েন করেছে! আপনি 0.03 টাকা পেয়েছেন।")
                user_data["referral_credited"] = True
                await update_user(user_id, user_data)

    # মেনু দেখানো
    if joined:
        txt = f"╔══════════════════╗\n<b>   EARNING BY REFER24 💸</b>\n╚══════════════════╝\n\n"
        txt += f"👋 স্বাগতম, <b>{user.full_name}</b>!\n"
        txt += "────────────────────\n"
        txt += "📌 প্রতি রেফারেল = 0.03 টাকা\n"
        txt += "📌 উইথড্র মিনিমাম = 1 টাকা\n"
        txt += "📌 চ্যানেল জয়েন না করলে একটিভিটি বন্ধ।\n"
        txt += "────────────────────\n"
        txt += "👨‍💻 নিচের বাটন থেকে কাজ শুরু করুন 👇"
        await update.message.reply_text(txt, reply_markup=main_menu(is_admin=(user_id == ADMIN_ID)), parse_mode="HTML")
    else:
        txt = f"╔══════════════════╗\n<b>   EARNING BY REFER24 💸</b>\n╚══════════════════╝\n\n"
        txt += f"👋 স্বাগতম, <b>{user.full_name}</b>!\n"
        txt += "🔒 বট ইউজ করতে নিচের <b>দুটি চ্যানেলে জয়েন</b> করে \"জয়েন করেছি\" বাটনে ক্লিক করুন।"
        await update.message.reply_text(txt, reply_markup=channel_join_keyboard(), parse_mode="HTML")

# ========== কলব্যাক হ্যান্ডলার ==========
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # ব্যান + চ্যানেল চেক (কিছু ক্ষেত্রে চেক স্কিপ)
    user = await get_user(user_id)
    if user and user.get("banned", False):
        await query.answer("⛔ আপনি ব্যানড!", show_alert=True)
        return

    # ---- check_join ----
    if data == "check_join":
        joined = await check_membership(user_id, context)
        if joined:
            user = await get_user(user_id)
            if not user.get("joined_channels", False):
                user["joined_channels"] = True
                # রেফারেল ক্রেডিট
                if user.get("referred_by") and not user.get("referral_credited", False):
                    ref_id = user["referred_by"]
                    ref_user = await get_user(ref_id)
                    if ref_user:
                        ref_user["balance"] = round(ref_user.get("balance", 0.0) + REFERRAL_BONUS, 2)
                        ref_user["referral_count"] = ref_user.get("referral_count", 0) + 1
                        await update_user(ref_id, ref_user)
                        await context.bot.send_message(ref_id,
                            f"🎉 আপনার রেফারেল @{query.from_user.username or query.from_user.full_name} চ্যানেলে জয়েন করেছে! আপনি 0.03 টাকা পেয়েছেন।")
                    user["referral_credited"] = True
                    await update_user(user_id, user)
            await query.edit_message_text(
                "✅ জয়েন সফল! এখন সম্পূর্ণ অ্যাক্সেস পাবেন।",
                reply_markup=main_menu(is_admin=(user_id == ADMIN_ID))
            )
        else:
            await query.answer("❗ এখনো জয়েন করেননি! দুই চ্যানেলেই জয়েন করুন।", show_alert=True)

    # ---- ব্যালেন্স ----
    elif data == "balance":
        if not await check_membership(user_id, context):
            await query.answer("❗ চ্যানেল জয়েন আবশ্যক!", show_alert=True)
            return
        user = await get_user(user_id)
        bal = user.get("balance", 0.0)
        await query.edit_message_text(
            f"💳 আপনার বর্তমান ব্যালেন্স: <b>{bal} টাকা</b>",
            parse_mode="HTML",
            reply_markup=back_button
        )

    # ---- রেফারেল লিংক ----
    elif data == "referral":
        if not await check_membership(user_id, context):
            await query.answer("❗ চ্যানেল জয়েন আবশ্যক!", show_alert=True)
            return
        link = f"https://t.me/earning_by_refer24_bot?start={user_id}"
        user = await get_user(user_id)
        count = user.get("referral_count", 0)
        txt = f"🔗 <b>তোমার রেফারেল লিংক:</b>\n<code>{link}</code>\n\n"
        txt += f"👥 মোট রেফারেল: {count}\n"
        txt += "👉 লিংক শেয়ার করে প্রতিবার 0.03 টাকা আয় করো।"
        await query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_button)

    # ---- উইথড্র ----
    elif data == "withdraw":
        if not await check_membership(user_id, context):
            await query.answer("❗ চ্যানেল জয়েন আবশ্যক!", show_alert=True)
            return
        user = await get_user(user_id)
        bal = user.get("balance", 0.0)
        if bal < MIN_WITHDRAW:
            await query.answer(f"❌ মিনিমাম {MIN_WITHDRAW} টাকা প্রয়োজন। আপনার ব্যালেন্স {bal} টাকা।", show_alert=True)
            return
        # উইথড্র রিকোয়েস্ট তৈরি
        data_obj = await get_data()
        w_list = data_obj.get("withdrawals", [])
        req_id = len(w_list) + 1
        req = {
            "id": req_id,
            "user_id": user_id,
            "username": query.from_user.username or query.from_user.full_name,
            "amount": bal,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
        w_list.append(req)
        data_obj["withdrawals"] = w_list
        await save_data(data_obj)
        # অ্যাডমিনকে নোটিফাই
        admin_text = f"🔔 <b>নতুন উইথড্র রিকোয়েস্ট</b> #{req_id}\n"
        admin_text += f"🧑 ইউজার: @{req['username']} (<code>{user_id}</code>)\n"
        admin_text += f"💰 পরিমাণ: {bal} টাকা\n"
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"approve_{req_id}"),
                InlineKeyboardButton("❌ রিজেক্ট", callback_data=f"reject_{req_id}")
            ]
        ])
        await context.bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="HTML")
        await query.edit_message_text(
            "✅ আপনার উইথড্র রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে। অনুমোদন পেলে ব্যালেন্স কাটা হবে।",
            reply_markup=back_button
        )

    # ---- উইথড্র হিস্টোরি ----
    elif data == "history":
        if not await check_membership(user_id, context):
            await query.answer("❗ চ্যানেল জয়েন আবশ্যক!", show_alert=True)
            return
        data_obj = await get_data()
        w_list = data_obj.get("withdrawals", [])
        my_requests = [r for r in w_list if r["user_id"] == user_id]
        if not my_requests:
            txt = "📭 কোনো উইথড্র রিকোয়েস্ট নেই।"
        else:
            txt = "📜 <b>তোমার উইথড্র হিস্টোরি</b>\n"
            for r in my_requests[-5:]:
                status_emoji = "⏳" if r["status"]=="pending" else ("✅" if r["status"]=="approved" else "❌")
                txt += f"#{r['id']} | {r['amount']} টাকা | {status_emoji} {r['status']}\n"
        await query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_button)

    # ---- হেল্প ----
    elif data == "help":
        txt = "🆘 <b>Earning By Refer24 বট হেল্প</b>\n\n"
        txt += "• রেফার করে 0.03 টাকা করে আয়।\n"
        txt += "• উইথড্র মিনিমাম 1 টাকা।\n"
        txt += "• চ্যানেল জয়েন না করলে বট কাজ করবে না।\n"
        txt += "• প্রশ্ন থাকলে @Admin এ যোগাযোগ করো।"
        await query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_button)

    # ---- ব্যাক টু মেইন ----
    elif data == "back_main":
        txt = "🔝 <b>মূল মেনুতে ফিরে এসেছো</b>"
        await query.edit_message_text(txt, reply_markup=main_menu(is_admin=(user_id == ADMIN_ID)), parse_mode="HTML")

    # ---- অ্যাডমিন প্যানেল (শুধু অ্যাডমিন) ----
    elif data == "admin_panel" and user_id == ADMIN_ID:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="broadcast_start")],
            [InlineKeyboardButton("💰 ব্যালেন্স যোগ", callback_data="add_balance_start")],
            [InlineKeyboardButton("💸 ব্যালেন্স কাট", callback_data="cut_balance_start")],
            [InlineKeyboardButton("🚫 ব্যান ইউজার", callback_data="ban_start")],
            [InlineKeyboardButton("🔓 আনব্যান ইউজার", callback_data="unban_start")],
            [InlineKeyboardButton("📋 পেন্ডিং উইথড্র", callback_data="pending_withdrawals")],
            [InlineKeyboardButton("🔙 ব্যাক", callback_data="back_main")]
        ])
        await query.edit_message_text("⚙️ <b>অ্যাডমিন প্যানেল</b>", reply_markup=kb, parse_mode="HTML")

    # ---- পেন্ডিং উইথড্র (অ্যাডমিন) ----
    elif data == "pending_withdrawals" and user_id == ADMIN_ID:
        data_obj = await get_data()
        pendings = [r for r in data_obj.get("withdrawals", []) if r["status"]=="pending"]
        if not pendings:
            await query.answer("কোনো পেন্ডিং উইথড্র নেই।", show_alert=True)
            return
        txt = "⏳ <b>পেন্ডিং উইথড্র</b>\n"
        for r in pendings:
            txt += f"#{r['id']} | @{r['username']} | {r['amount']} টাকা\n"
        await query.edit_message_text(txt, parse_mode="HTML", reply_markup=back_button)

    # ---- এপ্রুভ/রিজেক্ট উইথড্র (অ্যাডমিন) ----
    else:
        if data.startswith("approve_") or data.startswith("reject_"):
            if user_id != ADMIN_ID:
                return
            action, req_id = data.split("_")
            req_id = int(req_id)
            data_obj = await get_data()
            w_list = data_obj.get("withdrawals", [])
            req = next((r for r in w_list if r["id"]==req_id and r["status"]=="pending"), None)
            if not req:
                await query.answer("রিকোয়েস্ট পাওয়া যায়নি বা আগেই সিদ্ধান্ত নেওয়া হয়েছে।", show_alert=True)
                return
            if action == "approve":
                # ব্যালেন্স চেক করে কাটা
                usr = await get_user(req["user_id"])
                if usr and usr["balance"] >= req["amount"]:
                    usr["balance"] = round(usr["balance"] - req["amount"], 2)
                    await update_user(req["user_id"], usr)
                    req["status"] = "approved"
                    w_list = [r if r["id"]!=req_id else req for r in w_list]
                    data_obj["withdrawals"] = w_list
                    await save_data(data_obj)
                    await context.bot.send_message(req["user_id"], f"✅ আপনার {req['amount']} টাকা উইথড্র এপ্রুভ হয়েছে।")
                    await query.edit_message_text(
                        f"✅ #{req_id} এপ্রুভ করা হয়েছে।",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_panel")]])
                    )
                else:
                    req["status"] = "rejected"
                    w_list = [r if r["id"]!=req_id else req for r in w_list]
                    data_obj["withdrawals"] = w_list
                    await save_data(data_obj)
                    await context.bot.send_message(req["user_id"], f"❌ আপনার উইথড্র রিকোয়েস্ট রিজেক্ট হয়েছে (অপ্রতুল ব্যালেন্স)।")
                    await query.edit_message_text("❌ রিজেক্ট হয়েছে (ব্যালেন্স কম ছিল)।", reply_markup=back_button)
            elif action == "reject":
                req["status"] = "rejected"
                w_list = [r if r["id"]!=req_id else req for r in w_list]
                data_obj["withdrawals"] = w_list
                await save_data(data_obj)
                await context.bot.send_message(req["user_id"], f"❌ আপনার {req['amount']} টাকা উইথড্র রিজেক্ট হয়েছে।")
                await query.edit_message_text(f"❌ #{req_id} রিজেক্ট করা হয়েছে।", reply_markup=back_button)

# ========== কনভারসেশন হ্যান্ডলার (অ্যাডমিন) ==========
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id != ADMIN_ID: return
    await update.callback_query.edit_message_text("📢 <b>যে মেসেজটি সবাইকে পাঠাতে চান সেটি লিখুন:</b>", parse_mode="HTML")
    return BROADCAST

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ids = await get_all_users()
    msg = update.message
    count = 0
    for uid in user_ids:
        try:
            await context.bot.copy_message(chat_id=int(uid), from_chat_id=msg.chat_id, message_id=msg.message_id)
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ ব্রডকাস্ট সম্পন্ন: {count}/{len(user_ids)} ইউজার পেয়েছে।", reply_markup=main_menu(is_admin=True))
    return ConversationHandler.END

async def add_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id != ADMIN_ID: return
    await update.callback_query.edit_message_text("➕ <b>যার ব্যালেন্স যোগ করবেন তার ইউজার আইডি দিন:</b>", parse_mode="HTML")
    return ADD_BAL_USER

async def add_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["target_id"] = int(update.message.text)
    await update.message.reply_text("💰 <b>কত টাকা যোগ করবেন?</b>", parse_mode="HTML")
    return ADD_BAL_AMOUNT

async def add_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = float(update.message.text)
    target_id = context.user_data["target_id"]
    usr = await get_user(target_id)
    if not usr:
        await update.message.reply_text("❌ ইউজার পাওয়া যায়নি।")
    else:
        usr["balance"] = round(usr.get("balance", 0.0) + amount, 2)
        await update_user(target_id, usr)
        await update.message.reply_text(f"✅ {target_id} আইডির ব্যালেন্সে {amount} টাকা যোগ করা হয়েছে।", reply_markup=main_menu(is_admin=True))
    return ConversationHandler.END

async def cut_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id != ADMIN_ID: return
    await update.callback_query.edit_message_text("➖ <b>যার ব্যালেন্স কাটবেন তার ইউজার আইডি দিন:</b>", parse_mode="HTML")
    return CUT_BAL_USER

async def cut_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["target_id"] = int(update.message.text)
    await update.message.reply_text("💸 <b>কত টাকা কাটবেন?</b>", parse_mode="HTML")
    return CUT_BAL_AMOUNT

async def cut_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = float(update.message.text)
    target_id = context.user_data["target_id"]
    usr = await get_user(target_id)
    if not usr:
        await update.message.reply_text("❌ ইউজার পাওয়া যায়নি।")
    else:
        usr["balance"] = round(usr.get("balance", 0.0) - amount, 2)
        await update_user(target_id, usr)
        await update.message.reply_text(f"✅ {target_id} আইডির ব্যালেন্স থেকে {amount} টাকা কাটা হয়েছে।", reply_markup=main_menu(is_admin=True))
    return ConversationHandler.END

async def ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id != ADMIN_ID: return
    await update.callback_query.edit_message_text("🚫 <b>ব্যান করতে চান এমন ইউজার আইডি দিন:</b>", parse_mode="HTML")
    return BAN_USER

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = int(update.message.text)
    usr = await get_user(target_id)
    if not usr:
        await update.message.reply_text("❌ ইউজার পাওয়া যায়নি।")
    else:
        usr["banned"] = True
        await update_user(target_id, usr)
        await update.message.reply_text(f"⛔ {target_id} আইডি ব্যান করা হয়েছে।", reply_markup=main_menu(is_admin=True))
    return ConversationHandler.END

async def unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.from_user.id != ADMIN_ID: return
    await update.callback_query.edit_message_text("🔓 <b>আনব্যান করতে চান এমন ইউজার আইডি দিন:</b>", parse_mode="HTML")
    return UNBAN_USER

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = int(update.message.text)
    usr = await get_user(target_id)
    if not usr:
        await update.message.reply_text("❌ ইউজার পাওয়া যায়নি।")
    else:
        usr["banned"] = False
        await update_user(target_id, usr)
        await update.message.reply_text(f"✅ {target_id} আইডি আনব্যান করা হয়েছে।", reply_markup=main_menu(is_admin=True))
    return ConversationHandler.END

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ বাতিল করা হয়েছে।", reply_markup=main_menu(is_admin=True))
    return ConversationHandler.END

# ========== মেইন ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # কমান্ড (শুধু /start)
    app.add_handler(CommandHandler("start", start))

    # কলব্যাক হ্যান্ডলার
    app.add_handler(CallbackQueryHandler(callback_handler))

    # অ্যাডমিন কনভারসেশন
    admin_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(broadcast_start, pattern="^broadcast_start$"),
            CallbackQueryHandler(add_balance_start, pattern="^add_balance_start$"),
            CallbackQueryHandler(cut_balance_start, pattern="^cut_balance_start$"),
            CallbackQueryHandler(ban_start, pattern="^ban_start$"),
            CallbackQueryHandler(unban_start, pattern="^unban_start$"),
        ],
        states={
            BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)],
            ADD_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_user)],
            ADD_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_amount)],
            CUT_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, cut_balance_user)],
            CUT_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cut_balance_amount)],
            BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_user)],
            UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, unban_user)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin, pattern="^cancel_admin$")]
    )
    app.add_handler(admin_conv)

    # পোলিং শুরু
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
