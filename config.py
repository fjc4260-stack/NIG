# توکن و آیدی ادمین دیگه اینجا نوشته نمی‌شن (تا لو نرن)؛
# از "Environment Variables" توی پنل Render خونده می‌شن.
# برای اجرای لوکال روی کامپیوتر خودت، می‌تونی یه فایل .env بسازی یا
# قبل از اجرا این دو خط رو توی ترمینال بزنی:
#   export BOT_TOKEN="توکن_ربات"
#   export ADMIN_ID="آیدی_عددی_خودت"
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
