# iosGhost Telegram Builder Bot

بوت تيليجرام يحدّث سورس APT تلقائياً:
- يطلب **GitHub Username + Token** مرة واحدة ويخزنهم محلياً داخل `data/config.json` (غير مرفوع للـ Git).
- يعرض مستودعات GitHub لاختيار مستودع السورس، ويمكن تغييره لاحقاً.
- عند إرسال ملف `.deb`:
  - ينزّله إلى مجلد `debs/`
  - يحدّث `Packages` بشكل **Incremental** بدون حذف بيانات قديمة
  - ينشئ/يحدّث الضغطات: `Packages.gz` و `Packages.bz2` و `Packages.xz` و `Packages.zst` و `Packages.lzma` (حسب توفر الأدوات)
  - يحدّث `Release`
  - يحدث ملفات `depictions/` لنفس الـ deb
  - يرفع التغييرات إلى GitHub

## Railway Setup

- **المتغيرات (Variables)**:
  - `TELEGRAM_BOT_TOKEN`: توكن بوت تيليجرام
  - (اختياري) `ADMIN_CHAT_ID`: رقم حسابك في تيليجرام لتقييد الوصول

- **التشغيل**:
  - إذا Railway استخدمت `Procfile`: الخدمة تكون `worker`
  - أو مع `Dockerfile`: الخدمة تشغل `python bot.py` تلقائياً

## Bot Commands

- `/start`: بدء الإعدادات
- `/change_repo`: تغيير مستودع السورس المختار
- `/reset`: تصفير إعدادات GitHub (ما عدا admin)

## Notes (Security)

- لا تكتب أي توكنات داخل الملفات. استخدم Railway Variables فقط.
- `data/` متجاهل في `.gitignore` حتى لا ينرفع أي توكن.

