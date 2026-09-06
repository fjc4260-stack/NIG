"""
دیتابیس ربات نیگا — روی MongoDB Atlas (رایگان و مستقل از Render)
- هر گروه یه تنظیم «مدت زمان صبر» جدا داره
- هر کاربر توی هر گروه یه تعداد پوینت و زمان آخرین باری که گفته «نیگا» داره

نکته: آدرس اتصال دیتابیس از متغیر محیطی MONGODB_URI خونده می‌شه.
این آدرس رو از MongoDB Atlas بگیر و توی بخش Environment سرویس Render بذار؛
هیچ‌وقت مستقیم توی کد ننویسش.
"""
import os
from datetime import datetime

from pymongo import MongoClient, ReturnDocument

MONGODB_URI = os.environ.get("MONGODB_URI", "")
DEFAULT_COOLDOWN_SECONDS = 3600  # پیش‌فرض: ۱ ساعت

# ======================= تنظیمات مخزن نیگایی =======================
SILO_CAPACITY_PER_LEVEL = 20   # هر لول مخزن، ۲۰ تا به گنجایش اضافه می‌کنه
SILO_MAX_LEVEL = 6             # حداکثر لولی که هر مخزن می‌تونه بهش برسه
DEFAULT_SILO_BUY_PRICE = 10          # قیمت پیش‌فرض خرید یه مخزن جدید (لول پایه)
DEFAULT_SILO_UPGRADE_BASE_PRICE = 5  # قیمت پیش‌فرض ارتقای مخزن از لول ۱ به ۲
DEFAULT_SILO_UPGRADE_STEP = 3         # به ازای هر لول، این مقدار به قیمت ارتقای بعدی اضافه می‌شه (پلکانی)

_client = None
_db = None


def _get_db():
    """اتصال به Mongo رو (فقط یه بار) برقرار می‌کنه و شیء دیتابیس رو برمی‌گردونه."""
    global _client, _db
    if _db is None:
        if not MONGODB_URI:
            raise RuntimeError(
                "متغیر محیطی MONGODB_URI تنظیم نشده. "
                "آدرس اتصال MongoDB Atlas رو از پنل Atlas بگیر و توی بخش "
                "Environment سرویس Render (یا لوکال با export) قرارش بده."
            )
        _client = MongoClient(MONGODB_URI)
        _db = _client["niga_bot"]
    return _db


def init_db():
    """ایندکس‌های لازم برای جست‌وجوی سریع و جلوگیری از رکورد تکراری رو می‌سازه."""
    db = _get_db()
    db.users.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
    db.groups.create_index("chat_id", unique=True)
    db.bot_meta.create_index("key", unique=True)
    db.silos.create_index([("chat_id", 1), ("user_id", 1)])
    db.settings.create_index("chat_id", unique=True)


def _next_silo_id(db) -> int:
    """شمارنده‌ی افزایشی برای آیدی مخزن‌ها (شبیه AUTOINCREMENT توی SQLite)."""
    doc = db.counters.find_one_and_update(
        {"_id": "silo_id"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["seq"]


# ======================= گروه‌ها (برای پنل ادمین) =======================

def upsert_group(chat_id: int, title: str, chat_type: str):
    db = _get_db()
    db.groups.update_one(
        {"chat_id": chat_id},
        {
            "$set": {"title": title, "chat_type": chat_type, "active": True},
            "$setOnInsert": {"added_at": datetime.utcnow().isoformat(), "invite_link": None},
        },
        upsert=True,
    )


def mark_group_inactive(chat_id: int):
    db = _get_db()
    db.groups.update_one({"chat_id": chat_id}, {"$set": {"active": False}})


def list_groups() -> list:
    db = _get_db()
    docs = db.groups.find({"active": True}).sort("title", 1)
    return [{"chat_id": d["chat_id"], "title": d.get("title")} for d in docs]


def get_group_title(chat_id: int):
    db = _get_db()
    doc = db.groups.find_one({"chat_id": chat_id})
    return doc.get("title") if doc else None


def get_group_link(chat_id: int):
    """لینک ذخیره‌شده‌ی گروه رو برمی‌گردونه (اگه قبلاً ذخیره شده باشه)."""
    db = _get_db()
    doc = db.groups.find_one({"chat_id": chat_id})
    return doc.get("invite_link") if doc and doc.get("invite_link") else None


def set_group_link(chat_id: int, link: str):
    """لینک گروه رو ذخیره/به‌روزرسانی می‌کنه."""
    db = _get_db()
    db.groups.update_one({"chat_id": chat_id}, {"$set": {"invite_link": link}})


# ======================= متن‌های قابل‌ویرایش (bot_meta) =======================

def _get_meta(key: str):
    db = _get_db()
    doc = db.bot_meta.find_one({"key": key})
    return doc.get("value") if doc and doc.get("value") else None


def _set_meta(key: str, value: str):
    db = _get_db()
    db.bot_meta.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)


def get_guide_text():
    return _get_meta("guide_text")


def set_guide_text(text: str):
    _set_meta("guide_text", text)


def get_niga_success_text():
    return _get_meta("niga_success_text")


def set_niga_success_text(text: str):
    _set_meta("niga_success_text", text)


def get_nigaham_text():
    return _get_meta("nigaham_text")


def set_nigaham_text(text: str):
    _set_meta("nigaham_text", text)


def get_niga_wait_text():
    return _get_meta("niga_wait_text")


def set_niga_wait_text(text: str):
    _set_meta("niga_wait_text", text)


def get_niga_collect_text():
    return _get_meta("niga_collect_text")


def set_niga_collect_text(text: str):
    _set_meta("niga_collect_text", text)


def get_silo_prices() -> dict:
    """قیمت‌های خرید/ارتقای مخزن رو برمی‌گردونه؛ اگه تنظیم نشده باشه مقادیر پیش‌فرض."""
    value = _get_meta("silo_prices")
    if value:
        try:
            buy, base, step = (int(x) for x in value.split(","))
            return {"buy": buy, "upgrade_base": base, "upgrade_step": step}
        except Exception:
            pass
    return {
        "buy": DEFAULT_SILO_BUY_PRICE,
        "upgrade_base": DEFAULT_SILO_UPGRADE_BASE_PRICE,
        "upgrade_step": DEFAULT_SILO_UPGRADE_STEP,
    }


def set_silo_prices(buy: int, upgrade_base: int, upgrade_step: int):
    _set_meta("silo_prices", f"{buy},{upgrade_base},{upgrade_step}")


# ======================= تنظیمات هر گروه =======================

def get_cooldown(chat_id: int) -> int:
    db = _get_db()
    doc = db.settings.find_one({"chat_id": chat_id})
    return doc["cooldown_seconds"] if doc else DEFAULT_COOLDOWN_SECONDS


def set_cooldown(chat_id: int, seconds: int):
    db = _get_db()
    db.settings.update_one(
        {"chat_id": chat_id}, {"$set": {"cooldown_seconds": seconds}}, upsert=True
    )


# ======================= کاربران =======================

def _ensure_user_row(db, chat_id: int, user_id: int):
    """مطمئن می‌شه رکورد کاربر وجود داره، بدون تغییر دادن مقادیرِ موجود."""
    db.users.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$setOnInsert": {
                "points": 0,
                "last_used": None,
                "farms": 0,
                "workers": 0,
                "hidden": False,
                "silo_pool": 0,
                "name": None,
                "username": None,
            }
        },
        upsert=True,
    )


def get_user(chat_id: int, user_id: int) -> dict:
    db = _get_db()
    doc = db.users.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc:
        return {"points": doc.get("points", 0), "last_used": doc.get("last_used")}
    return {"points": 0, "last_used": None}


def get_points(chat_id: int, user_id: int) -> int:
    return get_user(chat_id, user_id)["points"]


# ======================= اقتصاد مزرعه (نیگا شاپ) =======================

def get_economy(chat_id: int, user_id: int) -> dict:
    """پوینت، تعداد مزرعه و تعداد نیگا(کارگر) این کاربر توی این گروه."""
    db = _get_db()
    doc = db.users.find_one({"chat_id": chat_id, "user_id": user_id})
    if doc:
        return {
            "points": doc.get("points", 0),
            "farms": doc.get("farms", 0) or 0,
            "workers": doc.get("workers", 0) or 0,
        }
    return {"points": 0, "farms": 0, "workers": 0}


def _add_clamped(field: str, chat_id: int, user_id: int, delta: int):
    """مقدار یه فیلد عددی رو کم/زیاد می‌کنه، ولی هیچ‌وقت زیر صفر نمی‌ره."""
    db = _get_db()
    _ensure_user_row(db, chat_id, user_id)
    doc = db.users.find_one({"chat_id": chat_id, "user_id": user_id})
    current = (doc.get(field) or 0) if doc else 0
    new_value = max(0, current + delta)
    db.users.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {field: new_value}})


def add_points(chat_id: int, user_id: int, delta: int):
    """پوینت کاربر رو کم/زیاد می‌کنه (هیچ‌وقت منفی نمی‌شه)."""
    _add_clamped("points", chat_id, user_id, delta)


def add_farms(chat_id: int, user_id: int, delta: int):
    """تعداد مزرعه‌ی کاربر رو کم/زیاد می‌کنه (هیچ‌وقت منفی نمی‌شه)."""
    _add_clamped("farms", chat_id, user_id, delta)


def add_workers(chat_id: int, user_id: int, delta: int):
    """تعداد «نیگا»های کاربر (کارگر مزرعه) رو کم/زیاد می‌کنه (هیچ‌وقت منفی نمی‌شه)."""
    _add_clamped("workers", chat_id, user_id, delta)


# ======================= مخزن نیگایی =======================

def add_silo(chat_id: int, user_id: int) -> int:
    """یه مخزن جدید (لول ۱) برای کاربر می‌سازه و آیدیشو برمی‌گردونه."""
    db = _get_db()
    _ensure_user_row(db, chat_id, user_id)
    new_id = _next_silo_id(db)
    db.silos.insert_one(
        {
            "_id": new_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "level": 1,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    return new_id


def list_silos(chat_id: int, user_id: int) -> list:
    """لیست مخزن‌های این کاربر توی این گروه (به ترتیب ساخت)."""
    db = _get_db()
    docs = db.silos.find({"chat_id": chat_id, "user_id": user_id}).sort("_id", 1)
    return [{"id": d["_id"], "level": d["level"]} for d in docs]


def get_silo(silo_id: int):
    """اطلاعات یه مخزن خاص رو برمی‌گردونه (برای چک مالکیت هنگام ارتقا)."""
    db = _get_db()
    doc = db.silos.find_one({"_id": silo_id})
    if not doc:
        return None
    return {
        "id": doc["_id"],
        "chat_id": doc["chat_id"],
        "user_id": doc["user_id"],
        "level": doc["level"],
    }


def upgrade_silo(silo_id: int) -> bool:
    """مخزن رو یه لول ارتقا می‌ده (اگه به حداکثر لول نرسیده باشه). خروجی: موفق بود یا نه."""
    db = _get_db()
    result = db.silos.update_one(
        {"_id": silo_id, "level": {"$lt": SILO_MAX_LEVEL}}, {"$inc": {"level": 1}}
    )
    return result.modified_count > 0


def get_silo_total_capacity(chat_id: int, user_id: int) -> int:
    """مجموع گنجایش همه‌ی مخزن‌های این کاربر توی این گروه."""
    db = _get_db()
    pipeline = [
        {"$match": {"chat_id": chat_id, "user_id": user_id}},
        {"$group": {"_id": None, "total_levels": {"$sum": "$level"}}},
    ]
    result = list(db.silos.aggregate(pipeline))
    total_levels = result[0]["total_levels"] if result else 0
    return total_levels * SILO_CAPACITY_PER_LEVEL


def get_silo_pool(chat_id: int, user_id: int) -> int:
    """میزان نیگاپوینتی که الان داخل مخزن‌هاست ولی هنوز جمع‌آوری نشده."""
    db = _get_db()
    doc = db.users.find_one({"chat_id": chat_id, "user_id": user_id})
    return doc.get("silo_pool", 0) if doc else 0


def set_silo_pool(chat_id: int, user_id: int, value: int):
    """میزان نیگاپوینتِ داخل مخزن رو مستقیم تنظیم می‌کنه (استفاده در تیک تولید مزرعه)."""
    db = _get_db()
    _ensure_user_row(db, chat_id, user_id)
    db.users.update_one(
        {"chat_id": chat_id, "user_id": user_id}, {"$set": {"silo_pool": max(0, value)}}
    )


def collect_silo_pool(chat_id: int, user_id: int) -> int:
    """هرچی داخل مخزن‌هاست رو خالی می‌کنه و مقدارشو برمی‌گردونه (برای دستور «جمع آوری نیگایی»)."""
    db = _get_db()
    _ensure_user_row(db, chat_id, user_id)
    doc = db.users.find_one({"chat_id": chat_id, "user_id": user_id})
    amount = (doc.get("silo_pool") or 0) if doc else 0
    if amount:
        db.users.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {"silo_pool": 0}})
    return amount


def set_hidden(chat_id: int, user_id: int, hidden: bool):
    """کاربر دارایی‌هاشو (با ریپلای زدن دیگران) پنهان/آشکار می‌کنه."""
    db = _get_db()
    _ensure_user_row(db, chat_id, user_id)
    db.users.update_one(
        {"chat_id": chat_id, "user_id": user_id}, {"$set": {"hidden": bool(hidden)}}
    )


def is_hidden(chat_id: int, user_id: int) -> bool:
    """آیا این کاربر دارایی‌هاشو پنهان کرده؟ (پیش‌فرض: نه)"""
    db = _get_db()
    doc = db.users.find_one({"chat_id": chat_id, "user_id": user_id})
    return bool(doc.get("hidden", False)) if doc else False


def list_farm_pairs() -> list:
    """
    برای هر کاربری که هم مزرعه هم نیگا داره، (chat_id, user_id, تعداد جفت) رو برمی‌گردونه.
    تعداد جفت = min(مزرعه, نیگا) — یعنی هر نیگا فقط رو یه مزرعه کار می‌کنه.
    """
    db = _get_db()
    docs = db.users.find({"farms": {"$gt": 0}, "workers": {"$gt": 0}})
    result = []
    for d in docs:
        pairs = min(d.get("farms", 0) or 0, d.get("workers", 0) or 0)
        if pairs > 0:
            result.append((d["chat_id"], d["user_id"], pairs))
    return result


def update_user_name(chat_id: int, user_id: int, name: str, username: str):
    db = _get_db()
    db.users.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$set": {"name": name, "username": username},
            "$setOnInsert": {
                "points": 0,
                "last_used": None,
                "farms": 0,
                "workers": 0,
                "hidden": False,
                "silo_pool": 0,
            },
        },
        upsert=True,
    )


def list_users_leaderboard(limit: int = 30) -> list:
    """مجموع پوینت هر کاربر، جمع‌شده روی همه‌ی گروه‌ها."""
    db = _get_db()
    pipeline = [
        {"$group": {"_id": "$user_id", "total": {"$sum": "$points"}, "name": {"$max": "$name"}}},
        {"$match": {"total": {"$gt": 0}}},
        {"$sort": {"total": -1}},
        {"$limit": limit},
    ]
    docs = db.users.aggregate(pipeline)
    return [{"user_id": d["_id"], "total": d["total"], "name": d.get("name")} for d in docs]


def list_users_in_group(chat_id: int, limit: int = 30) -> list:
    db = _get_db()
    docs = (
        db.users.find({"chat_id": chat_id, "points": {"$gt": 0}})
        .sort("points", -1)
        .limit(limit)
    )
    return [{"user_id": d["user_id"], "points": d["points"], "name": d.get("name")} for d in docs]


def try_use_niga(chat_id: int, user_id: int):
    """
    اگه اجازه داشته باشه، یه پوینت اضافه می‌کنه و زمانو ثبت می‌کنه.
    خروجی: (اجازه_داره: bool, پوینت_فعلی: int, ثانیه_باقیمانده: int)
    """
    cooldown = get_cooldown(chat_id)
    user = get_user(chat_id, user_id)
    now = datetime.utcnow()

    if user["last_used"]:
        last_used = datetime.fromisoformat(user["last_used"])
        elapsed = (now - last_used).total_seconds()
        if elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            return False, user["points"], remaining

    new_points = user["points"] + 1
    db = _get_db()
    db.users.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$set": {"points": new_points, "last_used": now.isoformat()},
            "$setOnInsert": {
                "farms": 0,
                "workers": 0,
                "hidden": False,
                "silo_pool": 0,
                "name": None,
                "username": None,
            },
        },
        upsert=True,
    )
    return True, new_points, 0


def format_duration(seconds: int) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} روز")
    if hours:
        parts.append(f"{hours} ساعت")
    if minutes:
        parts.append(f"{minutes} دقیقه")
    if not parts:
        parts.append(f"{secs if secs else 1} ثانیه")
    return " و ".join(parts)
