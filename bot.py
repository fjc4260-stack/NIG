"""
ربات نیگا 😄

قانون بازی:
- هرکی توی گروه (هرجای چت، بدون نیاز به ریپلای زدن به ربات) بگه «نیگا»
  یه پوینت می‌گیره و ربات با ریپلای بهش خبر می‌ده.
- بعدش تا یه مدت زمان مشخص نمی‌تونه دوباره پوینت بگیره؛ اگه زودتر
  دوباره بگه، ربات بهش می‌گه چقدر مونده.
- با گفتن «نیگاهام» هرکسی می‌تونه پوینت، مزرعه پنبه و نیگاهای خودشو ببینه.
- اگه روی پیام یه نفر ریپلای بزنه و بگه «نیگاهام»، دارایی‌های همون فرد
  نشون داده می‌شه — مگراینکه اون فرد با «نیگاهامو پنهان کن» جلوشو گرفته باشه
  (با «نیگاهامو نمایش بده» می‌تونه دوباره بازش کنه).
- گفتن «راهنما» (چه توی گروه چه توی پی‌وی) لیست دستورات رو نشون می‌ده.
- فقط ادمین ربات (صاحب ربات، نه ادمین‌های گروه) با دستور /settings
  می‌تونه مدت زمان صبر رو برای هر گروه تنظیم کنه، و از پنل /admin می‌تونه
  متن راهنما، پیام «یه پوینت گرفتی»، پیام «نیگاهام»، پیام «فعلا صبر کن»
  و قیمت‌های مخزن رو هم ویرایش کنه.
- از «نیگا شاپ» می‌شه «مخزن» هم خرید. نیگاپوینت‌هایی که از مزرعه تولید
  می‌شن، اول می‌رن داخل مخزن (نه مستقیم به حساب کاربر)؛ اگه کاربر مخزن
  نداشته باشه هیچ پوینتی تولید نمی‌شه. با گفتن «جمع آوری نیگایی»
  می‌شه پوینت‌های داخل همه‌ی مخزن‌ها رو یک‌جا جمع کرد. هر مخزن ۲۰ ظرفیت
  پایه داره و تا لول ۶ قابل ارتقاست (هر لول +۲۰ ظرفیت).
"""
import os
import re
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, ConversationHandler, ContextTypes, filters
)

import db
from config import BOT_TOKEN, ADMIN_ID

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SET_COOLDOWN = 1
EDIT_GUIDE = 2
EDIT_NIGA_MSG = 3
EDIT_NIGAHAM_MSG = 4
EDIT_WAIT_MSG = 5
EDIT_SILO_PRICES = 6
EDIT_COLLECT_MSG = 7

# کلمه‌ی «نیگا» به‌صورت یه کلمه‌ی جدا (نه بخشی از یه کلمه‌ی دیگه مثل «نیگاهام»)
NIGA_PATTERN = re.compile(r"\bنیگا\b")
NIGAHAM_PATTERN = re.compile(r"\bنیگاهام\b")
# وقتی کسی موقع ریپلای زدن به یه نفر، بگه «نیگاهاش» (سوم‌شخص) به‌جای «نیگاهام»
NIGAHASH_PATTERN = re.compile(r"\bنیگاهاش\b")
# وقتی داخل گروه اسم «ربات» رو صدا بزنن
BOT_NAME_PATTERN = re.compile(r"\bربات\b")
# وقتی داخل گپ خصوصی کسی بگه «راهنما»
GUIDE_PATTERN = re.compile(r"\bراهنما\b")
# وقتی داخل گروه کسی بگه «نیگا شاپ» (پنل مزرعه‌داری)
SHOP_PATTERN = re.compile(r"نیگا\s*شاپ")
# وقتی کسی بخواد نیگاپوینت‌های جمع‌شده توی مخزن‌هاشو جمع‌آوری کنه
COLLECT_PATTERN = re.compile(r"جمع\s*[آا]وری\s*نیگایی")
# وقتی کسی بخواد دارایی‌هاشو از دید بقیه (با ریپلای) پنهان/آشکار کنه
HIDE_PATTERN = re.compile(r"نیگاهامو\s*پنهان\s*کن")
UNHIDE_PATTERN = re.compile(r"نیگاهامو\s*نمایش\s*بده")

DEFAULT_GUIDE_TEXT = (
    "🤖 راهنمای ربات نیگا:\n\n"
    "من رو به یکی از گروه‌هایی که توش ادمینی اضافه کن و به‌عنوان ادمین نگه‌دار.\n\n"
    "📋 دستورات:\n"
    "«نیگا» → یه پوینت می‌گیری، ولی باید یه مدت صبر کنی تا دوباره بتونی.\n"
    "«نیگاهام» → دیدن پوینت، مزرعه پنبه و نیگاهات.\n"
    "روی پیام یه نفر ریپلای بزن و بگو «نیگاهام» → دیدن دارایی‌های اون فرد.\n"
    "«نیگاهامو پنهان کن» → دیگه هیچ‌کس با ریپلای نمی‌تونه دارایی‌هاتو ببینه.\n"
    "«نیگاهامو نمایش بده» → لغو پنهان‌کاری.\n"
    "«نیگا شاپ» → خرید/فروش مزرعه پنبه، نیگا و مخزن.\n"
    "«جمع آوری نیگایی» → جمع‌آوری نیگاپوینت‌هایی که توی مخزن‌هات جمع شده.\n\n"
    "🏺 نکته‌ی مخزن: پوینت‌هایی که از مزرعه تولید می‌شن اول می‌رن توی مخزن، نه مستقیم به حسابت. "
    "اگه مخزن نداشته باشی، پوینتی تولید نمی‌شه! برای گرفتنشون باید بگی «جمع آوری نیگایی». "
    "هر مخزن می‌تونه تا لول ۶ ارتقا پیدا کنه و هر لول ۲۰ تا به گنجایشش اضافه می‌کنه.\n\n"
    "«راهنما» → همین پیام."
)

DEFAULT_NIGA_SUCCESS_TEXT = (
    "🎯 یه پوینت گرفتی! الان {points} پوینت داری.\n"
    "⏳ تا {cooldown} دیگه نمی‌تونی دوباره بگی «نیگا»."
)

DEFAULT_NIGAHAM_TEXT = (
    "📊 {name} تا الان {points} پوینت داره.\n"
    "🌾 مزرعه پنبه: {farms}\n"
    "😄 نیگا: {workers}\n"
    "🏺 مخزن‌ها:\n{silos}"
)

DEFAULT_NIGA_WAIT_TEXT = (
    "🚫 نچ! هنوز {remaining} مونده تا بتونی دوباره پوینت بگیری.\n"
    "الان {points} پوینت داری."
)

DEFAULT_NIGA_COLLECT_TEXT = (
    "✅ نیگاپوینت‌هات جمع‌آوری شد! {collected} تا از مخزن‌هات جمع کردی.\n"
    "💰 الان {points} پوینت داری."
)

HIDDEN_ASSETS_TEXT = "🙈 این کاربر نیگاهاشو پنهان کرده."

# ======================= تنظیمات اقتصاد مزرعه (نیگا شاپ) =======================
# نیگا پوینت‌ها همون «پول» این اقتصادن. این مقادیر رو هر وقت خواستی همین‌جا عوض کن.
FARM_PRICE = 5           # قیمت خرید یه «مزرعه پنبه» (پوینت)
FARM_SELL_PRICE = 2      # قیمت فروش یه «مزرعه پنبه»
NIGA_ITEM_PRICE = 3      # قیمت خرید یه «نیگا» برای کار کردن روی مزرعه (پوینت)
NIGA_ITEM_SELL_PRICE = 1 # قیمت فروش یه «نیگا»
PASSIVE_INCOME_PER_PAIR = 2       # به ازای هر جفت (۱ مزرعه + ۱ نیگا) در هر تیک
PASSIVE_INCOME_INTERVAL_SECONDS = 60  # هر چند ثانیه یه بار تیک بخوره (پیش‌فرض: هر ۱ دقیقه)

PRESET_OPTIONS = [
    ("۱۰ دقیقه", 600),
    ("۳۰ دقیقه", 1800),
    ("۱ ساعت", 3600),
    ("۳ ساعت", 10800),
    ("۶ ساعت", 21600),
    ("۱۲ ساعت", 43200),
    ("۲۴ ساعت", 86400),
]


def silo_upgrade_cost(current_level: int) -> int:
    """قیمت ارتقای مخزن از current_level به current_level+1 (پلکانی، بر اساس تنظیمات پنل ادمین)."""
    prices = db.get_silo_prices()
    return prices["upgrade_base"] + prices["upgrade_step"] * (current_level - 1)


def is_bot_owner(user_id: int) -> bool:
    return user_id == ADMIN_ID


def render_niga_success_text(points: int, cooldown_seconds: int) -> str:
    """پیام «یه پوینت گرفتی» رو با متن قابل‌ویرایش (از پنل ادمین) می‌سازه."""
    template = db.get_niga_success_text() or DEFAULT_NIGA_SUCCESS_TEXT
    cooldown_str = db.format_duration(cooldown_seconds)
    try:
        return template.format(points=points, cooldown=cooldown_str)
    except Exception:
        # اگه ادمین متنی با پلیس‌هولدر اشتباه ذخیره کرده باشه، برنگردیم رو خطا
        return DEFAULT_NIGA_SUCCESS_TEXT.format(points=points, cooldown=cooldown_str)


def silos_summary_text(chat_id: int, user_id: int) -> str:
    """خلاصه‌ی وضعیت مخزن‌های یه کاربر (لول هرکدوم + میزان پرشدگی) برای نمایش توی «نیگاهام»."""
    silos = db.list_silos(chat_id, user_id)
    if not silos:
        return "هنوز هیچ مخزنی نداری (از «نیگا شاپ» بخر تا نیگاپوینت جمع بشه)."
    lines = []
    for i, s in enumerate(silos, 1):
        capacity = s["level"] * db.SILO_CAPACITY_PER_LEVEL
        lines.append(f"  {i}. لول {s['level']}/{db.SILO_MAX_LEVEL} (گنجایش {capacity})")
    total_capacity = sum(s["level"] for s in silos) * db.SILO_CAPACITY_PER_LEVEL
    pool = db.get_silo_pool(chat_id, user_id)
    lines.append(f"📦 داخل مخزن‌ها: {pool}/{total_capacity} (برای گرفتنش بگو «جمع آوری نیگایی»)")
    return "\n".join(lines)


def render_nigaham_text(name: str, econ: dict, silos_text: str) -> str:
    """پیام «نیگاهام» (نمایش دارایی) رو با متن قابل‌ویرایش (از پنل ادمین) می‌سازه."""
    template = db.get_nigaham_text() or DEFAULT_NIGAHAM_TEXT
    try:
        return template.format(name=name, points=econ["points"], farms=econ["farms"], workers=econ["workers"], silos=silos_text)
    except Exception:
        return DEFAULT_NIGAHAM_TEXT.format(name=name, points=econ["points"], farms=econ["farms"], workers=econ["workers"], silos=silos_text)


def render_niga_wait_text(points: int, remaining_seconds: int) -> str:
    """پیام محدودیت زمانی («فعلا صبر کن») رو با متن قابل‌ویرایش (از پنل ادمین) می‌سازه."""
    template = db.get_niga_wait_text() or DEFAULT_NIGA_WAIT_TEXT
    remaining_str = db.format_duration(remaining_seconds)
    try:
        return template.format(points=points, remaining=remaining_str)
    except Exception:
        return DEFAULT_NIGA_WAIT_TEXT.format(points=points, remaining=remaining_str)


def render_niga_collect_text(collected: int, points: int) -> str:
    """پیام «نیگاپوینت‌هات جمع‌آوری شد» رو با متن قابل‌ویرایش (از پنل ادمین) می‌سازه."""
    template = db.get_niga_collect_text() or DEFAULT_NIGA_COLLECT_TEXT
    try:
        return template.format(collected=collected, points=points)
    except Exception:
        return DEFAULT_NIGA_COLLECT_TEXT.format(collected=collected, points=points)


# ======================= دستورات پایه =======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = await context.bot.get_me()
    user = update.effective_user
    rows = [[InlineKeyboardButton("➕ افزودن به گروه", url=f"https://t.me/{me.username}?startgroup=true")]]

    await update.message.reply_text(
        "سلام! من ربات «نیگا» هستم 😄\n\n"
        "با دکمه‌ی زیر می‌تونی من رو به یکی از گروه‌هایی که توش ادمینی اضافه کنی.\n"
        "هرکی توی گروه بگه «نیگا» یه پوینت می‌گیره، ولی باید یه مدت صبر کنه تا دوباره بتونه پوینت بگیره.\n"
        "برای دیدن پوینت‌هات بگو «نیگاهام».",
        reply_markup=InlineKeyboardMarkup(rows)
    )
    if is_bot_owner(user.id):
        # پنل ادمین جدا از پیام استارت، فقط با دستور /admin یا دکمه‌ی زیر
        await update.message.reply_text("🛠 پنل مدیریت ربات:", reply_markup=admin_panel_keyboard())


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"آیدی عددی شما: `{update.effective_user.id}`", parse_mode="Markdown")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


# ======================= تنظیمات (فقط ادمین ربات) =======================

async def settings_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text("این دستور فقط داخل گروه کار می‌کنه.")
        return ConversationHandler.END
    if not is_bot_owner(update.effective_user.id):
        await update.message.reply_text("فقط ادمین ربات می‌تونه این تنظیم رو عوض کنه.")
        return ConversationHandler.END

    context.user_data["settings_target_chat"] = update.effective_chat.id
    current = db.get_cooldown(update.effective_chat.id)
    kb = [[InlineKeyboardButton(label, callback_data=f"cd:{seconds}")] for label, seconds in PRESET_OPTIONS]
    kb.append([InlineKeyboardButton("✏️ عدد دلخواه (دقیقه)", callback_data="cd:custom")])
    await update.message.reply_text(
        f"⏱ مدت زمان فعلی بین دو بار گفتن «نیگا»: {db.format_duration(current)}\n"
        "مدت جدید رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return SET_COOLDOWN


async def settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_bot_owner(query.from_user.id):
        await query.edit_message_text("فقط ادمین ربات می‌تونه این تنظیم رو عوض کنه.")
        return ConversationHandler.END

    target_chat_id = context.user_data.get("settings_target_chat", update.effective_chat.id)
    data = query.data.split(":", 1)[1]
    if data == "custom":
        await query.edit_message_text("عدد دقیقه رو به‌صورت پیام بفرست (مثلا 45):")
        return SET_COOLDOWN

    seconds = int(data)
    db.set_cooldown(target_chat_id, seconds)
    title = db.get_group_title(target_chat_id) or str(target_chat_id)
    await query.edit_message_text(f"✅ مدت زمان جدید برای «{title}» تنظیم شد: {db.format_duration(seconds)}")
    context.user_data.pop("settings_target_chat", None)
    return ConversationHandler.END


async def settings_custom_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_bot_owner(update.effective_user.id):
        return ConversationHandler.END
    try:
        minutes = int(update.message.text.strip())
        if minutes <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("لطفا فقط یه عدد صحیح مثبت (دقیقه) بفرست.")
        return SET_COOLDOWN

    target_chat_id = context.user_data.get("settings_target_chat", update.effective_chat.id)
    seconds = minutes * 60
    db.set_cooldown(target_chat_id, seconds)
    title = db.get_group_title(target_chat_id) or str(target_chat_id)
    await update.message.reply_text(f"✅ مدت زمان جدید برای «{title}» تنظیم شد: {db.format_duration(seconds)}")
    context.user_data.pop("settings_target_chat", None)
    return ConversationHandler.END


async def admin_setcd_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب گروه از داخل پنل ادمین برای تنظیم مدت زمان صبر، بدون نیاز به حضور تو اون گروه."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    chat_id = int(query.data.split(":")[2])
    context.user_data["settings_target_chat"] = chat_id
    title = db.get_group_title(chat_id) or str(chat_id)
    current = db.get_cooldown(chat_id)
    kb = [[InlineKeyboardButton(label, callback_data=f"cd:{seconds}")] for label, seconds in PRESET_OPTIONS]
    kb.append([InlineKeyboardButton("✏️ عدد دلخواه (دقیقه)", callback_data="cd:custom")])
    await query.edit_message_text(
        f"⏱ گروه «{title}» — مدت زمان فعلی: {db.format_duration(current)}\nمدت جدید رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return SET_COOLDOWN


# ======================= بازی اصلی =======================

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    chat = update.effective_chat
    user = update.effective_user
    text = update.message.text.strip()

    # ثبت/به‌روزرسانی گروه و نام کاربر (برای پنل ادمین)
    db.upsert_group(chat.id, chat.title or str(chat.id), chat.type)
    db.update_user_name(chat.id, user.id, user.full_name, user.username)

    # «نیگا شاپ» → باز کردن پنل خرید/فروش مزرعه (این باید قبل از چک «نیگا» بررسی بشه)
    if SHOP_PATTERN.search(text):
        await open_shop(update, context)
        return

    # «جمع آوری نیگایی» → خالی کردن مخزن(ها) و انتقال نیگاپوینت‌های جمع‌شده به حساب کاربر
    if COLLECT_PATTERN.search(text):
        total_capacity = db.get_silo_total_capacity(chat.id, user.id)
        if total_capacity <= 0:
            await update.message.reply_text(
                "🏺 هنوز هیچ مخزنی نداری! اول از «نیگا شاپ» یه مخزن بخر تا نیگاپوینت‌های مزرعه جمع بشن."
            )
            return
        collected = db.collect_silo_pool(chat.id, user.id)
        if collected <= 0:
            await update.message.reply_text("📦 مخزن‌هات فعلاً خالیه، چیزی برای جمع‌آوری نیست.")
            return
        db.add_points(chat.id, user.id, collected)
        new_econ = db.get_economy(chat.id, user.id)
        await update.message.reply_text(render_niga_collect_text(collected, new_econ["points"]))
        return

    # «راهنما» → همون متن راهنمای قابل‌ویرایش، حالا داخل گروه هم کار می‌کنه
    if GUIDE_PATTERN.search(text):
        guide_text = db.get_guide_text() or DEFAULT_GUIDE_TEXT
        await update.message.reply_text(guide_text)
        return

    # «نیگاهامو پنهان کن» → از الان کسی نمی‌تونه با ریپلای دارایی این کاربرو ببینه
    if HIDE_PATTERN.search(text):
        db.set_hidden(chat.id, user.id, True)
        await update.message.reply_text("🙈 از الان دارایی‌هات با ریپلای زدن برای بقیه قابل دیدن نیست.")
        return

    # «نیگاهامو نمایش بده» → برگردوندن حالت قبل (لغو پنهان‌کاری)
    if UNHIDE_PATTERN.search(text):
        db.set_hidden(chat.id, user.id, False)
        await update.message.reply_text("👀 دارایی‌هات دوباره برای بقیه با ریپلای زدن قابل دیدنه.")
        return

    # «نیگاهام» یا (موقع ریپلای) «نیگاهاش» → نمایش دارایی (پوینت/مزرعه/نیگا)
    # اگه روی پیام یه نفر دیگه ریپلای شده باشه، دارایی همون فرد نشون داده می‌شه
    # (مگراینکه اون فرد قبلاً با «نیگاهامو پنهان کن» دارایی‌شو پنهان کرده باشه)
    if NIGAHAM_PATTERN.search(text) or NIGAHASH_PATTERN.search(text):
        reply_to = update.message.reply_to_message
        has_reply_target = reply_to and reply_to.from_user and not reply_to.from_user.is_bot

        if NIGAHASH_PATTERN.search(text) and not has_reply_target:
            await update.message.reply_text("برای دیدن دارایی یه نفر، اول روی پیامش ریپلای بزن و بعد بگو «نیگاهاش».")
            return

        target = reply_to.from_user if has_reply_target else user

        if target.id != user.id and db.is_hidden(chat.id, target.id):
            await update.message.reply_text(HIDDEN_ASSETS_TEXT)
            return

        econ = db.get_economy(chat.id, target.id)
        silos_text = silos_summary_text(chat.id, target.id)
        await update.message.reply_text(render_nigaham_text(target.first_name, econ, silos_text))
        return

    # «نیگا» → گرفتن پوینت یا اعلام زمان باقیمانده
    if NIGA_PATTERN.search(text):
        allowed, points, remaining = db.try_use_niga(chat.id, user.id)
        if allowed:
            cooldown = db.get_cooldown(chat.id)
            await update.message.reply_text(render_niga_success_text(points, cooldown))
        else:
            await update.message.reply_text(render_niga_wait_text(points, remaining))
        return

    # وقتی کسی داخل گروه اسم «ربات» رو صدا بزنه
    if BOT_NAME_PATTERN.search(text):
        await update.message.reply_text("بله؟ 🤖 برای گرفتن پوینت بگو «نیگا»، برای دیدن پوینت‌هات بگو «نیگاهام».")
        return


async def track_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هر بار که وضعیت عضویت/ادمینی ربات توی یه گروه عوض بشه، این تابع صدا زده می‌شه."""
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status

    if new_status in ("member", "administrator"):
        db.upsert_group(chat.id, chat.title or str(chat.id), chat.type)
    elif new_status in ("left", "kicked"):
        db.mark_group_inactive(chat.id)
        return

    became_admin = new_status == "administrator" and old_status != "administrator"
    newly_added_as_member = new_status == "member" and old_status in ("left", "kicked")
    lost_admin = old_status == "administrator" and new_status == "member"

    try:
        if became_admin:
            # چه همون اول ادمین اضافه شده باشه، چه بعدا ادمین شده باشه
            await context.bot.send_message(chat.id, "✅ ربات فعال شد! از الان آماده‌ی بازی «نیگا» توی این گروهم.")
        elif newly_added_as_member:
            await context.bot.send_message(chat.id, "⚠️ برای فعال‌سازی، ربات باید ادمین گروه باشه.")
        elif lost_admin:
            await context.bot.send_message(chat.id, "⚠️ ادمینی من از گروه گرفته شد. برای فعال بودن دوباره باید ادمین بشم.")
    except Exception:
        logger.exception("could not send status message to chat %s", chat.id)


# ======================= نیگا شاپ (اقتصاد مزرعه‌داری) =======================
# نیگا پوینت‌ها همون پول این اقتصادن: کاربر با پوینت‌هاش «مزرعه پنبه» و «نیگا»
# می‌خره؛ وقتی هم مزرعه هم نیگا داشته باشه، خودکار براش پوینت فارم می‌شه.

def shop_status_text(first_name: str, econ: dict, chat_id: int, owner_id: int) -> str:
    silo_count = len(db.list_silos(chat_id, owner_id))
    total_capacity = db.get_silo_total_capacity(chat_id, owner_id)
    pool = db.get_silo_pool(chat_id, owner_id)
    return (
        f"👤 {first_name}\n"
        f"💰 پوینت: {econ['points']}\n"
        f"🌾 مزرعه پنبه: {econ['farms']}\n"
        f"😄 نیگا: {econ['workers']}\n"
        f"🏺 مخزن: {silo_count} تا (📦 {pool}/{total_capacity})"
    )


def shop_main_keyboard(owner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 خرید", callback_data=f"shop:buy:{owner_id}")],
        [InlineKeyboardButton("💰 فروش", callback_data=f"shop:sell:{owner_id}")],
        [InlineKeyboardButton("🏺 مخزن", callback_data=f"shop:silo:{owner_id}")],
        [InlineKeyboardButton("❌ بستن", callback_data=f"shop:close:{owner_id}")],
    ])


def shop_buy_keyboard(owner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🌾 مزرعه پنبه — {FARM_PRICE} پوینت", callback_data=f"shop:buyitem:farm:{owner_id}")],
        [InlineKeyboardButton(f"😄 نیگا — {NIGA_ITEM_PRICE} پوینت", callback_data=f"shop:buyitem:niga:{owner_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"shop:main:{owner_id}")],
    ])


def shop_sell_keyboard(owner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🌾 فروش مزرعه پنبه — {FARM_SELL_PRICE} پوینت", callback_data=f"shop:sellitem:farm:{owner_id}")],
        [InlineKeyboardButton(f"😄 فروش نیگا — {NIGA_ITEM_SELL_PRICE} پوینت", callback_data=f"shop:sellitem:niga:{owner_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"shop:main:{owner_id}")],
    ])


def silo_menu_keyboard(chat_id: int, owner_id: int) -> InlineKeyboardMarkup:
    prices = db.get_silo_prices()
    rows = []
    for silo in db.list_silos(chat_id, owner_id):
        if silo["level"] < db.SILO_MAX_LEVEL:
            cost = silo_upgrade_cost(silo["level"])
            rows.append([InlineKeyboardButton(
                f"⬆️ ارتقای مخزن #{silo['id']} (لول {silo['level']}→{silo['level']+1}) — {cost} پوینت",
                callback_data=f"shop:siloup:{silo['id']}:{owner_id}"
            )])
    rows.append([InlineKeyboardButton(f"➕ خرید مخزن جدید — {prices['buy']} پوینت", callback_data=f"shop:silobuy:{owner_id}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"shop:main:{owner_id}")])
    return InlineKeyboardMarkup(rows)


def silo_menu_text(chat_id: int, owner_id: int) -> str:
    silos = db.list_silos(chat_id, owner_id)
    if not silos:
        return "🏺 هنوز هیچ مخزنی نداری. بدون مخزن، نیگاپوینتی از مزرعه جمع نمی‌شه!"
    lines = ["🏺 مخزن‌های تو:"]
    for silo in silos:
        capacity = silo["level"] * db.SILO_CAPACITY_PER_LEVEL
        lines.append(f"  #{silo['id']} — لول {silo['level']}/{db.SILO_MAX_LEVEL} (گنجایش {capacity})")
    total_capacity = db.get_silo_total_capacity(chat_id, owner_id)
    pool = db.get_silo_pool(chat_id, owner_id)
    lines.append(f"\n📦 داخل مخزن‌ها: {pool}/{total_capacity}")
    return "\n".join(lines)


async def open_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """باز کردن پنل نیگا شاپ برای کاربری که توی گروه گفته «نیگا شاپ»."""
    chat = update.effective_chat
    user = update.effective_user
    econ = db.get_economy(chat.id, user.id)
    text = "🛒 نیگا شاپ\n\n" + shop_status_text(user.first_name, econ, chat.id, user.id)
    await update.message.reply_text(text, reply_markup=shop_main_keyboard(user.id))


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """این پنل فقط برای همون کاربری کار می‌کنه که با «نیگا شاپ» بازش کرده."""
    query = update.callback_query
    parts = query.data.split(":")
    # ساختار: shop:<action>[:<item>]:<owner_id>
    owner_id = int(parts[-1])
    action = parts[1]

    if query.from_user.id != owner_id:
        await query.answer("این پنل مال شما نیست؛ خودتون بگید «نیگا شاپ» تا پنل خودتون باز بشه.", show_alert=True)
        return
    await query.answer()

    chat_id = update.effective_chat.id

    if action == "main":
        econ = db.get_economy(chat_id, owner_id)
        text = "🛒 نیگا شاپ\n\n" + shop_status_text(query.from_user.first_name, econ, chat_id, owner_id)
        await query.edit_message_text(text, reply_markup=shop_main_keyboard(owner_id))
        return

    if action == "close":
        await query.edit_message_text("🛒 نیگا شاپ بسته شد. هروقت خواستی دوباره بگو «نیگا شاپ».")
        return

    if action == "buy":
        await query.edit_message_text("🛍 چی می‌خوای بخری؟", reply_markup=shop_buy_keyboard(owner_id))
        return

    if action == "sell":
        econ = db.get_economy(chat_id, owner_id)
        await query.edit_message_text(
            f"💰 چی می‌خوای بفروشی؟\n(الان داری: 🌾 {econ['farms']} مزرعه، 😄 {econ['workers']} نیگا)",
            reply_markup=shop_sell_keyboard(owner_id)
        )
        return

    if action == "buyitem":
        item = parts[2]
        price = FARM_PRICE if item == "farm" else NIGA_ITEM_PRICE
        econ = db.get_economy(chat_id, owner_id)
        if econ["points"] < price:
            await query.answer(f"پوینت کافی نداری! نیاز داری به {price} پوینت، فقط {econ['points']} تا داری.", show_alert=True)
            return
        db.add_points(chat_id, owner_id, -price)
        if item == "farm":
            db.add_farms(chat_id, owner_id, 1)
            bought_label = "🌾 یه مزرعه پنبه"
        else:
            db.add_workers(chat_id, owner_id, 1)
            bought_label = "😄 یه نیگا"
        new_econ = db.get_economy(chat_id, owner_id)
        await query.edit_message_text(
            f"✅ {bought_label} خریدی!\n\n" + shop_status_text(query.from_user.first_name, new_econ, chat_id, owner_id),
            reply_markup=shop_main_keyboard(owner_id)
        )
        return

    if action == "silo":
        await query.edit_message_text(
            silo_menu_text(chat_id, owner_id),
            reply_markup=silo_menu_keyboard(chat_id, owner_id)
        )
        return

    if action == "silobuy":
        price = db.get_silo_prices()["buy"]
        econ = db.get_economy(chat_id, owner_id)
        if econ["points"] < price:
            await query.answer(f"پوینت کافی نداری! نیاز داری به {price} پوینت، فقط {econ['points']} تا داری.", show_alert=True)
            return
        db.add_points(chat_id, owner_id, -price)
        db.add_silo(chat_id, owner_id)
        await query.edit_message_text(
            "✅ یه مخزن جدید (لول ۱) خریدی!\n\n" + silo_menu_text(chat_id, owner_id),
            reply_markup=silo_menu_keyboard(chat_id, owner_id)
        )
        return

    if action == "siloup":
        silo_id = int(parts[2])
        silo = db.get_silo(silo_id)
        if not silo or silo["chat_id"] != chat_id or silo["user_id"] != owner_id:
            await query.answer("این مخزن پیدا نشد!", show_alert=True)
            return
        if silo["level"] >= db.SILO_MAX_LEVEL:
            await query.answer("این مخزن از قبل به حداکثر لول رسیده!", show_alert=True)
            return
        cost = silo_upgrade_cost(silo["level"])
        econ = db.get_economy(chat_id, owner_id)
        if econ["points"] < cost:
            await query.answer(f"پوینت کافی نداری! نیاز داری به {cost} پوینت، فقط {econ['points']} تا داری.", show_alert=True)
            return
        db.add_points(chat_id, owner_id, -cost)
        db.upgrade_silo(silo_id)
        await query.edit_message_text(
            "✅ مخزن ارتقا پیدا کرد!\n\n" + silo_menu_text(chat_id, owner_id),
            reply_markup=silo_menu_keyboard(chat_id, owner_id)
        )
        return

    if action == "sellitem":
        item = parts[2]
        econ = db.get_economy(chat_id, owner_id)
        if item == "farm":
            if econ["farms"] <= 0:
                await query.answer("هیچ مزرعه‌ای نداری که بفروشی!", show_alert=True)
                return
            db.add_farms(chat_id, owner_id, -1)
            db.add_points(chat_id, owner_id, FARM_SELL_PRICE)
            sold_label = "🌾 یه مزرعه پنبه"
        else:
            if econ["workers"] <= 0:
                await query.answer("هیچ نیگایی نداری که بفروشی!", show_alert=True)
                return
            db.add_workers(chat_id, owner_id, -1)
            db.add_points(chat_id, owner_id, NIGA_ITEM_SELL_PRICE)
            sold_label = "😄 یه نیگا"
        new_econ = db.get_economy(chat_id, owner_id)
        await query.edit_message_text(
            f"✅ {sold_label} فروختی!\n\n" + shop_status_text(query.from_user.first_name, new_econ, chat_id, owner_id),
            reply_markup=shop_main_keyboard(owner_id)
        )
        return


async def farm_income_job(context: ContextTypes.DEFAULT_TYPE):
    """
    هر ۱ دقیقه اجرا می‌شه: به هرکی هم مزرعه هم نیگا داره، نیگاپوینت فارم‌شده رو
    (نه مستقیم به پوینتش، بلکه) داخل مخزن‌هاش می‌ریزه.
    - اگه کاربر اصلاً مخزن نداشته باشه، هیچ پوینتی تولید/جمع نمی‌شه.
    - اگه مخزن‌هاش پر باشن (به حداکثر گنجایش رسیده باشن)، تولید متوقف می‌شه.
    - اگه کمتر از حداکثر باشه، بازم تولید ادامه پیدا می‌کنه (تا سقف گنجایش).
    """
    for chat_id, user_id, pairs in db.list_farm_pairs():
        if pairs <= 0:
            continue
        total_capacity = db.get_silo_total_capacity(chat_id, user_id)
        if total_capacity <= 0:
            # مخزن نداره → نیگاپوینتی جمع نمی‌شه
            continue
        pool = db.get_silo_pool(chat_id, user_id)
        if pool >= total_capacity:
            # مخزن(ها) پره → تولید متوقفه
            continue
        income = pairs * PASSIVE_INCOME_PER_PAIR
        db.set_silo_pool(chat_id, user_id, min(total_capacity, pool + income))


async def get_group_link(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """لینک عمومی یا لینک دعوت گروه رو برمی‌گردونه (در صورت وجود)."""
    try:
        chat = await context.bot.get_chat(chat_id)
    except Exception:
        chat = None

    if chat is not None and chat.username:
        return f"https://t.me/{chat.username}"
    if chat is not None and chat.invite_link:
        db.set_group_link(chat_id, chat.invite_link)
        return chat.invite_link

    cached = db.get_group_link(chat_id)
    if cached:
        return cached

    try:
        link = await context.bot.export_chat_invite_link(chat_id)
        db.set_group_link(chat_id, link)
        return link
    except Exception:
        return None


# ======================= پنل ادمین (فقط صاحب ربات) =======================

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 لیست گروه‌ها", callback_data="admin:groups")],
        [InlineKeyboardButton("👥 لیست کاربران (کل)", callback_data="admin:users")],
        [InlineKeyboardButton("⚙️ تنظیمات ربات", callback_data="admin:panel_settings")],
    ])


def admin_settings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ تنظیمات محدودیت زمانی", callback_data="admin:settings")],
        [InlineKeyboardButton("📝 ویرایش متن راهنما", callback_data="admin:editguide")],
        [InlineKeyboardButton("✏️ ویرایش پیام «یه پوینت گرفتی»", callback_data="admin:editnigamsg")],
        [InlineKeyboardButton("📊 ویرایش پیام «نیگاهام»", callback_data="admin:editnigaham")],
        [InlineKeyboardButton("⏳ ویرایش پیام «فعلا صبر کن»", callback_data="admin:editwaitmsg")],
        [InlineKeyboardButton("🏺 تنظیم قیمت مخزن", callback_data="admin:editsiloprices")],
        [InlineKeyboardButton("📦 ویرایش پیام «جمع‌آوری نیگایی»", callback_data="admin:editcollectmsg")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin:back")],
    ])


async def admin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🛠 پنل ادمین:", reply_markup=admin_panel_keyboard())


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return
    await query.answer()
    data = query.data

    if data == "admin:back":
        await query.edit_message_text("🛠 پنل ادمین:", reply_markup=admin_panel_keyboard())
        return

    if data == "admin:groups":
        groups = db.list_groups()
        if not groups:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:back")]])
            await query.edit_message_text("هنوز تو هیچ گروهی نیستم.", reply_markup=kb)
            return

        lines = [f"📋 ربات الان تو {len(groups)} گروهه. برای دیدن کاربراش روی اسمش بزن:\n"]
        for i, g in enumerate(groups, 1):
            title = g["title"] or str(g["chat_id"])
            link = await get_group_link(context, g["chat_id"])
            link_line = link if link else "لینک در دسترس نیست (شاید ربات ادمین نیست)"
            lines.append(f"{i}. {title}\n🔗 {link_line}")

        kb = [
            [InlineKeyboardButton(g["title"] or str(g["chat_id"]), callback_data=f"admin:group:{g['chat_id']}")]
            for g in groups
        ]
        kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:back")])
        await query.edit_message_text(
            "\n\n".join(lines),
            reply_markup=InlineKeyboardMarkup(kb),
            disable_web_page_preview=True
        )
        return

    if data == "admin:users":
        users = db.list_users_leaderboard(limit=30)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:back")]])
        if not users:
            await query.edit_message_text("هنوز هیچ‌کس پوینتی نگرفته.", reply_markup=kb)
            return
        lines = ["👥 لیست کاربران (مجموع پوینت روی همه‌ی گروه‌ها):"]
        for i, u in enumerate(users, 1):
            name = u["name"] or str(u["user_id"])
            lines.append(f"{i}. {name} — {u['total']} پوینت")
        await query.edit_message_text("\n".join(lines), reply_markup=kb)
        return

    if data.startswith("admin:group:"):
        chat_id = int(data.split(":")[2])
        title = db.get_group_title(chat_id) or str(chat_id)
        users = db.list_users_in_group(chat_id, limit=30)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست گروه‌ها", callback_data="admin:groups")]])
        if not users:
            await query.edit_message_text(f"👥 گروه «{title}»:\nهنوز کسی پوینت نگرفته.", reply_markup=kb)
            return
        lines = [f"👥 گروه «{title}»:"]
        for i, u in enumerate(users, 1):
            name = u["name"] or str(u["user_id"])
            lines.append(f"{i}. {name} — {u['points']} پوینت")
        await query.edit_message_text("\n".join(lines), reply_markup=kb)
        return

    if data == "admin:panel_settings":
        await query.edit_message_text("⚙️ تنظیمات ربات:", reply_markup=admin_settings_menu_keyboard())
        return

    if data == "admin:settings":
        groups = db.list_groups()
        if not groups:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel_settings")]])
            await query.edit_message_text("هنوز تو هیچ گروهی نیستم.", reply_markup=kb)
            return
        kb = [
            [InlineKeyboardButton(g["title"] or str(g["chat_id"]), callback_data=f"admin:setcd:{g['chat_id']}")]
            for g in groups
        ]
        kb.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:panel_settings")])
        await query.edit_message_text(
            "⏱ برای کدوم گروه می‌خوای مدت زمان صبر رو تنظیم کنی؟",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return


async def editguide_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش متنِ راهنما، فقط برای ادمین ربات."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    current = db.get_guide_text() or DEFAULT_GUIDE_TEXT
    await query.edit_message_text(
        f"📝 متن فعلی راهنما:\n\n{current}\n\n"
        "متن جدید رو به‌صورت پیام بفرست (یا /cancel برای لغو):"
    )
    return EDIT_GUIDE


async def editguide_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    new_text = update.message.text.strip()
    if not new_text:
        await update.message.reply_text("متن نمی‌تونه خالی باشه، دوباره بفرست:")
        return EDIT_GUIDE
    db.set_guide_text(new_text)
    await update.message.reply_text("✅ متن راهنما بروزرسانی شد.")
    return ConversationHandler.END


async def editnigamsg_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش متنِ پیام «یه پوینت گرفتی»، فقط برای ادمین ربات."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    current = db.get_niga_success_text() or DEFAULT_NIGA_SUCCESS_TEXT
    await query.edit_message_text(
        f"✏️ متن فعلی پیام «یه پوینت گرفتی»:\n\n{current}\n\n"
        "متن جدید رو بفرست. می‌تونی از این پلیس‌هولدرها استفاده کنی:\n"
        "{points} = تعداد پوینت فعلی\n"
        "{cooldown} = مدت زمان باقیمانده تا پوینت بعدی\n"
        "(یا /cancel برای لغو)"
    )
    return EDIT_NIGA_MSG


async def editnigamsg_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    new_text = update.message.text.strip()
    if not new_text:
        await update.message.reply_text("متن نمی‌تونه خالی باشه، دوباره بفرست:")
        return EDIT_NIGA_MSG
    # یه تست سریع که پلیس‌هولدرهای اشتباه فرمت رو همین‌جا بگیریم
    try:
        new_text.format(points=1, cooldown="۱ ساعت")
    except Exception:
        await update.message.reply_text(
            "⚠️ متن فرمتش درست نیست (فقط از {points} و {cooldown} استفاده کن). دوباره بفرست:"
        )
        return EDIT_NIGA_MSG
    db.set_niga_success_text(new_text)
    await update.message.reply_text("✅ متن پیام «یه پوینت گرفتی» بروزرسانی شد.")
    return ConversationHandler.END


async def editnigaham_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش متنِ پیام «نیگاهام» (نمایش دارایی)، فقط برای ادمین ربات."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    current = db.get_nigaham_text() or DEFAULT_NIGAHAM_TEXT
    await query.edit_message_text(
        f"📊 متن فعلی پیام «نیگاهام»:\n\n{current}\n\n"
        "متن جدید رو به‌صورت پیام بفرست. می‌تونی از این پلیس‌هولدرها استفاده کنی:\n"
        "{name} = اسم فرد\n"
        "{points} = تعداد پوینت\n"
        "{farms} = تعداد مزرعه پنبه\n"
        "{workers} = تعداد نیگا (کارگر)\n"
        "{silos} = خلاصه‌ی وضعیت مخزن‌ها\n"
        "(یا /cancel برای لغو)"
    )
    return EDIT_NIGAHAM_MSG


async def editnigaham_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    new_text = update.message.text.strip()
    if not new_text:
        await update.message.reply_text("متن نمی‌تونه خالی باشه، دوباره بفرست:")
        return EDIT_NIGAHAM_MSG
    try:
        new_text.format(name="تست", points=1, farms=1, workers=1, silos="نمونه")
    except Exception:
        await update.message.reply_text(
            "⚠️ متن فرمتش درست نیست (فقط از {name}, {points}, {farms}, {workers}, {silos} استفاده کن). دوباره بفرست:"
        )
        return EDIT_NIGAHAM_MSG
    db.set_nigaham_text(new_text)
    await update.message.reply_text("✅ متن پیام «نیگاهام» بروزرسانی شد.")
    return ConversationHandler.END


async def editwaitmsg_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش متنِ پیام محدودیت زمانی («فعلا صبر کن»)، فقط برای ادمین ربات."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    current = db.get_niga_wait_text() or DEFAULT_NIGA_WAIT_TEXT
    await query.edit_message_text(
        f"⏳ متن فعلی پیام «فعلا صبر کن»:\n\n{current}\n\n"
        "متن جدید رو به‌صورت پیام بفرست. می‌تونی از این پلیس‌هولدرها استفاده کنی:\n"
        "{remaining} = مدت زمان باقیمانده\n"
        "{points} = تعداد پوینت فعلی\n"
        "(یا /cancel برای لغو)"
    )
    return EDIT_WAIT_MSG


async def editwaitmsg_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    new_text = update.message.text.strip()
    if not new_text:
        await update.message.reply_text("متن نمی‌تونه خالی باشه، دوباره بفرست:")
        return EDIT_WAIT_MSG
    try:
        new_text.format(remaining="۱ ساعت", points=1)
    except Exception:
        await update.message.reply_text(
            "⚠️ متن فرمتش درست نیست (فقط از {remaining} و {points} استفاده کن). دوباره بفرست:"
        )
        return EDIT_WAIT_MSG
    db.set_niga_wait_text(new_text)
    await update.message.reply_text("✅ متن پیام «فعلا صبر کن» بروزرسانی شد.")
    return ConversationHandler.END


async def editsiloprices_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش قیمت‌های مخزن (خرید + پایه/پله‌ی ارتقا)، فقط برای ادمین ربات."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    prices = db.get_silo_prices()
    await query.edit_message_text(
        f"🏺 قیمت‌های فعلی مخزن:\n"
        f"خرید مخزن جدید: {prices['buy']} پوینت\n"
        f"قیمت پایه ارتقا (لول ۱→۲): {prices['upgrade_base']} پوینت\n"
        f"افزایش پله‌ای هر لول: {prices['upgrade_step']} پوینت\n\n"
        "قیمت جدید رو به‌صورت سه عدد با کاما بفرست: خرید,پایه_ارتقا,پله_ارتقا\n"
        "مثال: 10,5,3\n"
        "(یا /cancel برای لغو)"
    )
    return EDIT_SILO_PRICES


async def editsiloprices_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    raw = update.message.text.strip().replace("،", ",")
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 3:
        await update.message.reply_text("⚠️ باید دقیقا سه عدد با کاما بفرستی، مثلا: 10,5,3\nدوباره بفرست:")
        return EDIT_SILO_PRICES
    try:
        buy, base, step = (int(p) for p in parts)
        if buy <= 0 or base <= 0 or step < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ هر سه مقدار باید عدد صحیح مثبت باشن (پله می‌تونه صفر باشه). دوباره بفرست:")
        return EDIT_SILO_PRICES
    db.set_silo_prices(buy, base, step)
    await update.message.reply_text(
        f"✅ قیمت‌های مخزن بروزرسانی شد.\nخرید: {buy} | پایه ارتقا: {base} | پله: {step}"
    )
    return ConversationHandler.END


async def editcollectmsg_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ویرایش متنِ پیام «جمع‌آوری نیگایی»، فقط برای ادمین ربات."""
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("این پنل فقط برای صاحب رباته.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    current = db.get_niga_collect_text() or DEFAULT_NIGA_COLLECT_TEXT
    await query.edit_message_text(
        f"📦 متن فعلی پیام «جمع‌آوری نیگایی»:\n\n{current}\n\n"
        "متن جدید رو به‌صورت پیام بفرست. می‌تونی از این پلیس‌هولدرها استفاده کنی:\n"
        "{collected} = تعداد نیگاپوینتی که همین الان جمع‌آوری شد\n"
        "{points} = مجموع پوینت فعلی کاربر (بعد از جمع‌آوری)\n"
        "(یا /cancel برای لغو)"
    )
    return EDIT_COLLECT_MSG


async def editcollectmsg_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    new_text = update.message.text.strip()
    if not new_text:
        await update.message.reply_text("متن نمی‌تونه خالی باشه، دوباره بفرست:")
        return EDIT_COLLECT_MSG
    try:
        new_text.format(collected=1, points=1)
    except Exception:
        await update.message.reply_text(
            "⚠️ متن فرمتش درست نیست (فقط از {collected} و {points} استفاده کن). دوباره بفرست:"
        )
        return EDIT_COLLECT_MSG
    db.set_niga_collect_text(new_text)
    await update.message.reply_text("✅ متن پیام «جمع‌آوری نیگایی» بروزرسانی شد.")
    return ConversationHandler.END


# ======================= راهنما داخل گپ خصوصی =======================

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربری داخل گپ خصوصی کلمه‌ی «راهنما» رو بنویسه."""
    if not update.message or not update.message.text:
        return
    if GUIDE_PATTERN.search(update.message.text.strip()):
        text = db.get_guide_text() or DEFAULT_GUIDE_TEXT
        await update.message.reply_text(text)


# ======================= اجرای ربات =======================

def main():
    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        print("⚠️ لطفا اول توکن ربات رو توی فایل config.py وارد کن.")
        return

    db.init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("admin", admin_entry))
    app.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    settings_conv = ConversationHandler(
        entry_points=[
            CommandHandler("settings", settings_entry),
            CallbackQueryHandler(admin_setcd_entry, pattern=r"^admin:setcd:-?\d+$"),
        ],
        states={
            SET_COOLDOWN: [
                CallbackQueryHandler(settings_choice, pattern="^cd:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, settings_custom_minutes),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(settings_conv)

    editguide_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(editguide_entry, pattern="^admin:editguide$")],
        states={
            EDIT_GUIDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, editguide_receive)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(editguide_conv)

    editnigamsg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(editnigamsg_entry, pattern="^admin:editnigamsg$")],
        states={
            EDIT_NIGA_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, editnigamsg_receive)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(editnigamsg_conv)

    editnigaham_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(editnigaham_entry, pattern="^admin:editnigaham$")],
        states={
            EDIT_NIGAHAM_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, editnigaham_receive)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(editnigaham_conv)

    editwaitmsg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(editwaitmsg_entry, pattern="^admin:editwaitmsg$")],
        states={
            EDIT_WAIT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, editwaitmsg_receive)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(editwaitmsg_conv)

    editsiloprices_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(editsiloprices_entry, pattern="^admin:editsiloprices$")],
        states={
            EDIT_SILO_PRICES: [MessageHandler(filters.TEXT & ~filters.COMMAND, editsiloprices_receive)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(editsiloprices_conv)

    editcollectmsg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(editcollectmsg_entry, pattern="^admin:editcollectmsg$")],
        states={
            EDIT_COLLECT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, editcollectmsg_receive)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(editcollectmsg_conv)

    # این هندلر باید بعد از مکالمه‌ها ثبت بشه تا کال‌بک‌های admin:setcd:...، admin:editguide و admin:editnigamsg اول به دست خود مکالمه برسن
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin:"))

    # پنل نیگا شاپ (خرید/فروش مزرعه)
    app.add_handler(CallbackQueryHandler(shop_callback, pattern="^shop:"))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        handle_group_message
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_private_message
    ))

    # تیک خودکار فارم‌کردن پوینت (هر کاربری که هم مزرعه هم نیگا داشته باشه)
    if app.job_queue is not None:
        app.job_queue.run_repeating(
            farm_income_job,
            interval=PASSIVE_INCOME_INTERVAL_SECONDS,
            first=PASSIVE_INCOME_INTERVAL_SECONDS
        )
    else:
        print(
            "⚠️ JobQueue در دسترس نیست، فارم خودکار پوینت غیرفعاله. "
            "برای فعال‌سازیش این رو نصب کن: pip install \"python-telegram-bot[job-queue]\""
        )

    # روی Render (سرویس وب) این متغیر خودکار ست می‌شه؛ یعنی اینجا داریم
    # روی Render اجرا می‌شیم و باید به‌جای polling از webhook استفاده کنیم.
    external_url = os.environ.get("RENDER_EXTERNAL_URL")
    port = int(os.environ.get("PORT", "10000"))

    if external_url:
        print(f"🤖 ربات نیگا روی Render با webhook روشن شد: {external_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"{external_url}/{BOT_TOKEN}",
        )
    else:
        # اجرای لوکال روی کامپیوتر خودت (برای تست)
        print("🤖 ربات نیگا (حالت polling، لوکال) روشن شد و در حال اجراست...")
        app.run_polling()


if __name__ == "__main__":
    main()
