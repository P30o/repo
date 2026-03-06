import os
import subprocess
import time
from pathlib import Path
from logger import logger
import config
import utils
import keyboard
from telegram import TelegramBot

class BotHandlers:
    def __init__(self, bot: TelegramBot):
        self.bot = bot
    
    def welcome_user(self, chat_id: int, cfg: dict) -> None:
        if cfg.get("github_token"):
            repo_name = cfg.get("repo_full_name", "غير مضبوط")
            queue_size = len(cfg.get("queue", []))
            self.bot.send_message(
                chat_id,
                f"✨ *مرحباً بك في بوت بناء السورس!*\n\n"
                f"📦 *الحالة:* جاهز للعمل\n"
                f"🏠 *المستودع:* `{repo_name}`\n"
                f"📋 *في الانتظار:* {queue_size} ملفات\n\n"
                f"اختر من الأزرار أدناه:",
                reply_markup=keyboard.main_menu_keyboard(queue_size)
            )
        else:
            self.bot.send_message(
                chat_id,
                "🎉 *مرحباً بك في بوت بناء السورس الشامل!*\n\n"
                "✨ *مميزات البوت:*\n"
                "• رفع ملفات .deb لبناء سورس Cydia/Sileo\n"
                "• رفع صور للأيقونات والخلفيات\n"
                "• تخصيص هوية السورس\n"
                "• رفع تلقائي لـ GitHub\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🚀 *للبدء:* أرسل توكن GitHub الخاص بك\n"
                "   (احصل عليه من: Settings > Developer settings > Personal access tokens)",
                reply_markup=keyboard.cancel_keyboard()
            )
            config.save_user_config(chat_id, {**cfg, "flow": config.FLOW_STATES["WAIT_TOKEN"]})
    
    def handle_start(self, chat_id: int, cfg: dict) -> None:
        logger.info(f"/start command from user {chat_id}")
        self.welcome_user(chat_id, cfg)
    
    def handle_logout(self, chat_id: int, cfg: dict) -> None:
        logger.info(f"User {chat_id} logging out")
        utils.cleanup_temp_files(chat_id)
        new_cfg = config.clear_user_config(chat_id)
        self.bot.send_message(
            chat_id,
            "✅ تم تسجيل الخروج بنجاح.\nشكراً لاستخدامك البوت!",
            reply_markup=keyboard.remove_keyboard()
        )
    
    def handle_queue(self, chat_id: int, cfg: dict) -> None:
        queue = cfg.get("queue", [])
        if not queue:
            self.bot.send_message(
                chat_id,
                "⚠️ قائمة الانتظار فارغة!\n"
                "أرسل ملفات .deb أو صور أولاً.",
                reply_markup=keyboard.main_menu_keyboard(0)
            )
            return
        
        self.bot.send_message(
            chat_id,
            f"⏳ جاري معالجة {len(queue)} ملفات...\n"
            "يرجى الانتظار هذا قد يستغرق beberapa دقيقة...",
            reply_markup=keyboard.main_menu_keyboard(len(queue))
        )
        
        success_count = 0
        failed_files = []
        
        for item in queue:
            path = item["path"]
            action = item["action"]
            filename = os.path.basename(path)
            
            logger.info(f"Processing: {filename} with action {action}")
            ok, result = self.run_builder_action(path, cfg, action)
            
            if ok:
                success_count += 1
                logger.info(f"Successfully processed: {filename}")
            else:
                failed_files.append(filename)
                logger.error(f"Failed to process {filename}: {result}")
                self.bot.send_message(
                    chat_id,
                    f"❌ فشل بناء: {filename}\n{result[:500]}"
                )
        
        if success_count > 0:
            self.bot.send_message(chat_id, "🚀 جاري الرفع لـ GitHub...")
            
            ok2, err2 = self.sync_and_push(cfg, f"Update: {success_count} files")
            
            if ok2:
                repo_url = cfg.get("pages_base_url", "")
                self.bot.send_message(
                    chat_id,
                    f"✅ *تم بنجاح!*\n\n"
                    f"• تم تحديث {success_count} ملفات\n"
                    f"• [فتح السورس]({repo_url})",
                    reply_markup=keyboard.main_menu_keyboard(0)
                )
                cfg["queue"] = []
                config.save_user_config(chat_id, cfg)
                utils.cleanup_temp_files(chat_id)
            else:
                self.bot.send_message(
                    chat_id,
                    f"❌ فشل الرفع لـ GitHub:\n{err2[:500]}",
                    reply_markup=keyboard.main_menu_keyboard(len(queue))
                )
        else:
            self.bot.send_message(
                chat_id,
                "❌ فشل معالجة كل الملفات",
                reply_markup=keyboard.main_menu_keyboard(len(queue))
            )
    
    def handle_clear_queue(self, chat_id: int, cfg: dict) -> None:
        queue_size = len(cfg.get("queue", []))
        utils.cleanup_temp_files(chat_id)
        cfg["queue"] = []
        config.save_user_config(chat_id, cfg)
        
        self.bot.send_message(
            chat_id,
            f"🗑️ تم إفراغ قائمة الانتظار\n"
            f"({queue_size} ملفات كانت في الانتظار)",
            reply_markup=keyboard.main_menu_keyboard(0)
        )
    
    def handle_branding(self, chat_id: int, cfg: dict) -> None:
        branding = cfg.get("branding", {})
        
        self.bot.send_message(
            chat_id,
            "🎨 *تخصيص هوية السورس*\n\n"
            f"📝 *اسم السورس:* {branding.get('repo_name', 'غير مضبوط')}\n"
            f"👤 *المطور:* {branding.get('developer', 'غير مضبوط')}\n"
            f"✋ *المسؤول:* {branding.get('maintainer', 'غير مضبوط')}\n"
            f"📄 *الوصف:* {branding.get('description', 'غير مضبوط')[:50]}...\n\n"
            "اختر ما تريد تعديله:",
            reply_markup=keyboard.branding_menu_keyboard()
        )
    
    def handle_branding_name(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "📝 *تغيير اسم السورس*\n\n"
            "أرسل الاسم الجديد للسورس:",
            reply_markup=keyboard.cancel_keyboard()
        )
        cfg["flow"] = config.FLOW_STATES["BRANDING_NAME"]
        config.save_user_config(chat_id, cfg)
    
    def handle_branding_dev(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "👤 *تغيير اسم المطور*\n\n"
            "أرسل اسم المطور الجديد:",
            reply_markup=keyboard.cancel_keyboard()
        )
        cfg["flow"] = config.FLOW_STATES["BRANDING_DEV"]
        config.save_user_config(chat_id, cfg)
    
    def handle_branding_main(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "✋ *تغيير اسم المسؤول*\n\n"
            "أرسل اسم المسؤول الجديد:",
            reply_markup=keyboard.cancel_keyboard()
        )
        cfg["flow"] = config.FLOW_STATES["BRANDING_MAIN"]
        config.save_user_config(chat_id, cfg)
    
    def handle_branding_desc(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "📄 *تغيير وصف السورس*\n\n"
            "أرسل الوصف الجديد للسورس:",
            reply_markup=keyboard.cancel_keyboard()
        )
        cfg["flow"] = config.FLOW_STATES["BRANDING_DESC"]
        config.save_user_config(chat_id, cfg)
    
    def handle_repo_settings(self, chat_id: int, cfg: dict) -> None:
        repo = cfg.get("repo_full_name", "غير مضبوط")
        branch = cfg.get("repo_branch", "main")
        url = cfg.get("pages_base_url", "غير مضبوط")
        
        self.bot.send_message(
            chat_id,
            f"⚙️ *إعدادات المستودع*\n\n"
            f"🏠 *المستودع:* `{repo}`\n"
            f"🌿 *الفرع:* `{branch}`\n"
            f"🔗 *الرابط:* [فتح]({url})\n\n"
            "اختر الإعداد الذي تريد تغييره:",
            reply_markup=keyboard.repo_settings_keyboard()
        )
    
    def handle_change_repo(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "🔄 *تغيير المستودع*\n\n"
            "أرسل اسم المستودع الجديد بصيغة:\n"
            "`username/repo-name`\n\n"
            "مثال: `iosghost/my-repo`",
            reply_markup=keyboard.cancel_keyboard()
        )
        cfg["flow"] = config.FLOW_STATES["SETUP_REPO"]
        config.save_user_config(chat_id, cfg)
    
    def handle_change_branch(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "🌿 *تغيير الفرع*\n\n"
            "أراسم اسم الفرع الجديد:\n"
            "(الافتراضي: main)",
            reply_markup=keyboard.cancel_keyboard()
        )
        cfg["flow"] = "brancing_branch"
        config.save_user_config(chat_id, cfg)
    
    def handle_repo_url(self, chat_id: int, cfg: dict) -> None:
        url = cfg.get("pages_base_url", "")
        if url:
            self.bot.send_message(
                chat_id,
                f"🔗 *رابط السورس:*\n\n"
                f"[فتح السورس]({url})",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
        else:
            self.bot.send_message(
                chat_id,
                "⚠️ لم يتم إعداد رابط السورس بعد.\n"
                "يرجى إعداد المستودع أولاً.",
                reply_markup=keyboard.repo_settings_keyboard()
            )
    
    def handle_show_settings(self, chat_id: int, cfg: dict) -> None:
        branding = cfg.get("branding", {})
        
        settings_text = "📋 *إعدادات المستودع*\n\n"
        settings_text += f"🏠 *المستودع:* `{cfg.get('repo_full_name', 'غير مضبوط')}`\n"
        settings_text += f"🌿 *الفرع:* `{cfg.get('repo_branch', 'main')}`\n"
        settings_text += f"🔗 *الرابط:* {cfg.get('pages_base_url', 'غير مضبوط')}\n\n"
        settings_text += "🎨 *هوية السورس:*\n"
        settings_text += f"• الاسم: {branding.get('repo_name')}\n"
        settings_text += f"• المطور: {branding.get('developer')}\n"
        settings_text += f"• المسؤول: {branding.get('maintainer')}\n"
        settings_text += f"• الوصف: {branding.get('description')[:50]}...\n"
        
        self.bot.send_message(
            chat_id,
            settings_text,
            reply_markup=keyboard.repo_settings_keyboard()
        )
    
    def handle_status(self, chat_id: int, cfg: dict) -> None:
        queue = cfg.get("queue", [])
        
        status_text = "📊 *حالة المستودع*\n\n"
        status_text += f"🏠 *المستودع:* `{cfg.get('repo_full_name', 'غير مضبوط')}`\n"
        status_text += f"👤 *المستخدم:* {cfg.get('github_login', 'غير مسجل')}\n"
        status_text += f"📋 *في الانتظار:* {len(queue)} ملفات\n"
        
        if queue:
            status_text += "\n📦 *الملفات في الانتظار:*\n"
            for item in queue[:5]:
                status_text += f"• {os.path.basename(item['path'])}\n"
            if len(queue) > 5:
                status_text += f"... و {len(queue) - 5} ملفات أخرى\n"
        
        self.bot.send_message(
            chat_id,
            status_text,
            reply_markup=keyboard.main_menu_keyboard(len(queue))
        )
    
    def handle_back(self, chat_id: int, cfg: dict) -> None:
        self.welcome_user(chat_id, cfg)
    
    def handle_token_input(self, chat_id: int, text: str, cfg: dict) -> None:
        login = utils.verify_github_token(text)
        if login:
            cfg["github_token"] = text
            cfg["github_login"] = login
            cfg["flow"] = config.FLOW_STATES["WAIT_REPO"]
            config.save_user_config(chat_id, cfg)
            
            self.bot.send_message(
                chat_id,
                f"✅ *تم التحقق من التوكن!*\n\n"
                f"👤 *اليوزر:* {login}\n\n"
                "أرسل الآن اسم المستودع بصيغة:\n"
                "`username/repo-name`\n\n"
                "مثال: `iosghost/my-repo`",
                reply_markup=keyboard.cancel_keyboard()
            )
        else:
            self.bot.send_message(
                chat_id,
                "❌ *فشل التحقق من التوكن*\n\n"
                "تأكد من أن التوكن صحيح ولم ينتهِ صلاحيته.\n"
                "أرسل التوكن مرة أخرى:",
                reply_markup=keyboard.cancel_keyboard()
            )
    
    def handle_repo_input(self, chat_id: int, text: str, cfg: dict) -> None:
        token = cfg.get("github_token")
        repo_info = utils.get_repo_info(token, text)
        
        if repo_info:
            cfg["repo_full_name"] = text
            cfg["pages_base_url"] = f"https://{text.split('/')[0]}.github.io/{text.split('/')[1]}"
            cfg["flow"] = config.FLOW_STATES["READY"]
            config.save_user_config(chat_id, cfg)
            
            self.bot.send_message(
                chat_id,
                f"🎉 *تم إعداد المستودع بنجاح!*\n\n"
                f"🏠 *المستودع:* `{text}`\n"
                f"🔗 *رابط السورس:* [فتح]({cfg['pages_base_url']})\n\n"
                "✨ الآن يمكنك:\n"
                "• رفع ملفات .deb\n"
                "• رفع صور للأصول\n"
                "• تخصيص هوية السورس",
                reply_markup=keyboard.main_menu_keyboard(0)
            )
        else:
            self.bot.send_message(
                chat_id,
                "❌ *المستودع غير موجود*\n\n"
                "تأكد من:\n"
                "1. اسم المستودع صحيح\n"
                "2. لديك صلاحيات الوصول إليه\n\n"
                "أرسل اسم المستودع مرة أخرى:",
                reply_markup=keyboard.cancel_keyboard()
            )
    
    def handle_branding_input(self, chat_id: int, text: str, cfg: dict) -> None:
        flow = cfg.get("flow")
        branding = cfg.get("branding", {})
        
        if flow == config.FLOW_STATES["BRANDING_NAME"]:
            branding["repo_name"] = text
            msg = "✅ تم تغيير اسم السورس!"
        elif flow == config.FLOW_STATES["BRANDING_DEV"]:
            branding["developer"] = text
            msg = "✅ تم تغيير اسم المطور!"
        elif flow == config.FLOW_STATES["BRANDING_MAIN"]:
            branding["maintainer"] = text
            msg = "✅ تم تغيير اسم المسؤول!"
        elif flow == config.FLOW_STATES["BRANDING_DESC"]:
            branding["description"] = text
            msg = "✅ تم تغيير وصف السورس!"
        else:
            msg = "⚠️ حدث خطأ غير متوقع"
        
        cfg["branding"] = branding
        cfg["flow"] = config.FLOW_STATES["READY"]
        config.save_user_config(chat_id, cfg)
        
        self.bot.send_message(chat_id, msg, reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", []))))
    
    def handle_setup_repo_input(self, chat_id: int, text: str, cfg: dict) -> None:
        self.handle_repo_input(chat_id, text, cfg)
    
    def handle_branch_input(self, chat_id: int, text: str, cfg: dict) -> None:
        cfg["repo_branch"] = text.strip() or "main"
        cfg["flow"] = config.FLOW_STATES["READY"]
        config.save_user_config(chat_id, cfg)
        
        self.bot.send_message(
            chat_id,
            f"✅ تم تغيير الفرع إلى: `{cfg['repo_branch']}`",
            reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
        )
    
    def handle_upload_deb(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "📦 *رفع ملف .deb*\n\n"
            "أرسل ملف .deb الآن:\n"
            "• يجب أن يكون الملف صالحاً\n"
            "• يدعم جميع معمارية iOS",
            reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
        )
    
    def handle_upload_image(self, chat_id: int, cfg: dict) -> None:
        self.bot.send_message(
            chat_id,
            "🖼️ *رفع صورة للأصول*\n\n"
            "أرسل الصورة الآن:\n"
            "• سيتم حفظها في مجلد assets\n"
            "• يمكنك تخصيص اسم الصورة بعد الرفع",
            reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
        )
    
    def handle_image_rename(self, chat_id: int, text: str, cfg: dict) -> None:
        if "pending_image" not in cfg:
            self.bot.send_message(
                chat_id,
                "⚠️ لا توجد صورة معلقة لإعادة التسمية.\n"
                "ارفع صورة جديدة.",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
            return
        
        new_name = utils.sanitize_filename(text)
        if not new_name:
            self.bot.send_message(
                chat_id,
                "❌ اسم غير صالح. حاول مرة أخرى:",
                reply_markup=keyboard.cancel_keyboard()
            )
            return
        
        pending = cfg["pending_image"]
        old_path = pending["path"]
        
        # Get extension from original file
        import os
        ext = os.path.splitext(old_path)[1]
        if not new_name.endswith(ext):
            new_name = new_name + ext
        
        new_path = str(config.ASSETS_DIR / new_name)
        
        try:
            os.rename(old_path, new_path)
            cfg["queue"].append({"path": new_path, "action": "--add-asset"})
            del cfg["pending_image"]
            cfg["flow"] = config.FLOW_STATES["READY"]
            config.save_user_config(chat_id, cfg)
            
            self.bot.send_message(
                chat_id,
                f"✅ *تم إعادة تسمية الصورة!*\n\n"
                f"الاسم الجديد: `{new_name}`\n"
                f"تمت إضافتها للانتظار.",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
        except Exception as e:
            logger.error(f"Error renaming image: {e}")
            self.bot.send_message(
                chat_id,
                f"❌ حدث خطأ: {str(e)}",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
    
    def handle_document(self, chat_id: int, doc: dict, cfg: dict) -> None:
        if cfg.get("flow") != config.FLOW_STATES["READY"]:
            self.bot.send_message(
                chat_id,
                "⚠️ يرجى إكمال الإعداد أولاً.",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
            return
        
        file_name = doc.get("file_name", "file")
        file_id = doc.get("file_id")
        
        if not file_name.lower().endswith(".deb"):
            self.bot.send_message(
                chat_id,
                "⚠️ هذا الملف ليس .deb\n"
                "يرجى إرسال ملف .deb فقط.",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
            return
        
        self.bot.send_message(
            chat_id,
            f"⏳ جاري تحميل {file_name}...",
            reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
        )
        
        try:
            file_info = self.bot.get_file(file_id)
            file_path = file_info.get("file_path")
            
            if not file_path:
                raise Exception("Failed to get file path")
            
            user_tmp = config.TMP_DIR / str(chat_id)
            user_tmp.mkdir(exist_ok=True)
            dest = user_tmp / file_name
            self.bot.download_file(file_path, str(dest))
            
            deb_info = utils.get_deb_info(str(dest))
            if not deb_info:
                raise Exception("Failed to read deb info")
            
            cfg["queue"].append({
                "path": str(dest),
                "action": "--update-one",
                "filename": file_name,
                "package": deb_info.get("Package", "unknown"),
                "version": deb_info.get("Version", "unknown")
            })
            config.save_user_config(chat_id, cfg)
            
            self.bot.send_message(
                chat_id,
                f"✅ *تم إضافة الملف للانتظار!*\n\n"
                f"📦 *الملف:* {file_name}\n"
                f"📋 *الحزمة:* {deb_info.get('Package')}\n"
                f"📌 *الإصدار:* {deb_info.get('Version')}\n\n"
                f"📋 *في الانتظار:* {len(cfg['queue'])} ملفات",
                reply_markup=keyboard.main_menu_keyboard(len(cfg["queue"]))
            )
            
        except Exception as e:
            logger.error(f"Error processing deb: {e}")
            self.bot.send_message(
                chat_id,
                f"❌ *حدث خطأ:*\n{str(e)}",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
    
    def handle_photo(self, chat_id: int, photos: list, cfg: dict) -> None:
        if cfg.get("flow") != config.FLOW_STATES["READY"]:
            self.bot.send_message(
                chat_id,
                "⚠️ يرجى إكمال الإعداد أولاً.",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
            return
        
        photo = photos[-1]
        file_id = photo.get("file_id")
        
        self.bot.send_message(
            chat_id,
            "⏳ جاري تحميل الصورة...",
            reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
        )
        
        try:
            file_info = self.bot.get_file(file_id)
            file_path = file_info.get("file_path")
            
            if not file_path:
                raise Exception("Failed to get file path")
            
            user_tmp = config.TMP_DIR / str(chat_id)
            user_tmp.mkdir(exist_ok=True)
            
            ext = ".jpg"
            if file_path.endswith(".png"):
                ext = ".png"
            
            file_name = f"img_{int(time.time())}{ext}"
            dest = user_tmp / file_name
            
            self.bot.download_file(file_path, str(dest))
            
            self.bot.send_message(
                chat_id,
                f"✅ *تم تحميل الصورة!*\n\n"
                f"هل تريد تخصيص اسم الصورة؟\n"
                f"• أرسل الاسم الجديد بدون امتداد\n"
                f"• أو اضغط 'تخطي' للاسم الافتراضي",
                reply_markup={
                    "keyboard": [["تخطي"], ["\u274c إلغاء"]],
                    "resize_keyboard": True
                }
            )
            
            cfg["pending_image"] = {"path": str(dest), "original_name": file_name}
            cfg["flow"] = config.FLOW_STATES["RENAME_IMAGE"]
            config.save_user_config(chat_id, cfg)
            
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            self.bot.send_message(
                chat_id,
                f"❌ *حدث خطأ:*\n{str(e)}",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
    
    def handle_skip_rename(self, chat_id: int, cfg: dict) -> None:
        if "pending_image" not in cfg:
            self.welcome_user(chat_id, cfg)
            return
        
        pending = cfg["pending_image"]
        
        # Move from temp to assets
        dest = config.ASSETS_DIR / pending["original_name"]
        import shutil
        shutil.move(pending["path"], str(dest))
        
        cfg["queue"].append({
            "path": str(dest),
            "action": "--add-asset",
            "filename": pending["original_name"]
        })
        del cfg["pending_image"]
        cfg["flow"] = config.FLOW_STATES["READY"]
        config.save_user_config(chat_id, cfg)
        
        self.bot.send_message(
            chat_id,
            f"✅ *تمت إضافة الصورة للانتظار!*\n\n"
            f"📋 *في الانتظار:* {len(cfg['queue'])} ملفات",
            reply_markup=keyboard.main_menu_keyboard(len(cfg["queue"]))
        )
    
    def run_builder_action(self, file_path: str, config_dict: dict, action: str) -> tuple[bool, str]:
        # Clean the script file
        script_path = config.BASE_DIR / "ghost_update.sh"
        if script_path.exists():
            try:
                with open(script_path, "rb") as f:
                    content = f.read().replace(b"\r", b"")
                with open(script_path, "wb") as f:
                    f.write(content)
            except Exception as e:
                logger.warning(f"Could not clean script: {e}")
        
        env = os.environ.copy()
        branding = config_dict.get("branding", {})
        
        env["GHOST_BASE_URL"] = config_dict.get("pages_base_url", "")
        env["GHOST_AUTHOR"] = branding.get("developer", "Developer")
        env["GHOST_MAINTAINER"] = branding.get("maintainer", "Maintainer")
        env["GHOST_REPO_NAME"] = branding.get("repo_name", "My Repo")
        env["GHOST_REPO_DESC"] = branding.get("description", "A custom repository.")
        
        cmd = ["bash", str(script_path), action, file_path]
        
        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=str(config.BASE_DIR)
            )
            output = (result.stdout or "") + (result.stderr or "")
            logger.info(f"Builder action '{action}' completed with code {result.returncode}")
            return (result.returncode == 0), output[-2000:]
        except Exception as e:
            logger.error(f"Builder action failed: {e}")
            return False, str(e)
    
    def sync_and_push(self, config_dict: dict, commit_msg: str) -> tuple[bool, str]:
        owner, repo = config_dict["repo_full_name"].split("/", 1)
        token = config_dict["github_token"]
        branch = config_dict.get("repo_branch", "main")
        
        remote = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
        
        try:
            base_dir = config.BASE_DIR
            
            # Initialize git if needed
            if not (base_dir / ".git").exists():
                subprocess.run(
                    ["git", "init"],
                    check=False,
                    cwd=str(base_dir),
                    capture_output=True
                )
            
            subprocess.run(
                ["git", "config", "user.name", "RepoBot"],
                check=False,
                cwd=str(base_dir)
            )
            subprocess.run(
                ["git", "config", "user.email", "bot@repobuilder.io"],
                check=False,
                cwd=str(base_dir)
            )
            
            # Set remote
            subprocess.run(
                ["git", "remote", "remove", "origin"],
                check=False,
                cwd=str(base_dir)
            )
            subprocess.run(
                ["git", "remote", "add", "origin", remote],
                check=True,
                cwd=str(base_dir)
            )
            
            # Add all files
            subprocess.run(
                ["git", "add", "."],
                check=True,
                cwd=str(base_dir)
            )
            
            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                check=False,
                cwd=str(base_dir)
            )
            
            # Push
            result = subprocess.run(
                ["git", "push", "-f", "origin", f"HEAD:{branch}"],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(base_dir)
            )
            
            output = (result.stdout or "") + (result.stderr or "")
            success = result.returncode == 0
            
            if success:
                logger.info(f"Successfully pushed to {owner}/{repo}")
            else:
                logger.error(f"Push failed: {output}")
            
            return success, output[-1000:]
            
        except Exception as e:
            logger.error(f"Sync and push failed: {e}")
            return False, str(e)
    
    def process_message(self, chat_id: int, message: dict) -> None:
        cfg = config.load_user_config(chat_id)
        text = message.get("text", "").strip()
        
        # Handle cancel
        if text == "❌ إلغاء":
            if "pending_image" in cfg:
                import os
                try:
                    os.remove(cfg["pending_image"]["path"])
                except:
                    pass
                del cfg["pending_image"]
            
            cfg["flow"] = config.FLOW_STATES["READY"]
            config.save_user_config(chat_id, cfg)
            self.welcome_user(chat_id, cfg)
            return
        
        # Handle skip (for image rename)
        if text == "تخطي":
            self.handle_skip_rename(chat_id, cfg)
            return
        
        # Handle flow-based input
        flow = cfg.get("flow")
        
        if flow == config.FLOW_STATES["WAIT_TOKEN"]:
            self.handle_token_input(chat_id, text, cfg)
            return
        
        if flow == config.FLOW_STATES["WAIT_REPO"]:
            self.handle_repo_input(chat_id, text, cfg)
            return
        
        if flow == config.FLOW_STATES["BRANDING_NAME"]:
            self.handle_branding_input(chat_id, text, cfg)
            return
        
        if flow == config.FLOW_STATES["BRANDING_DEV"]:
            self.handle_branding_input(chat_id, text, cfg)
            return
        
        if flow == config.FLOW_STATES["BRANDING_MAIN"]:
            self.handle_branding_input(chat_id, text, cfg)
            return
        
        if flow == config.FLOW_STATES["BRANDING_DESC"]:
            self.handle_branding_input(chat_id, text, cfg)
            return
        
        if flow == config.FLOW_STATES["SETUP_REPO"]:
            self.handle_setup_repo_input(chat_id, text, cfg)
            return
        
        if flow == "brancing_branch":
            self.handle_branch_input(chat_id, text, cfg)
            return
        
        if flow == config.FLOW_STATES["RENAME_IMAGE"]:
            self.handle_image_rename(chat_id, text, cfg)
            return
        
        # Handle menu commands
        if text == "/start":
            self.handle_start(chat_id, cfg)
            return
        
        if text == "🚪 خروج" or text == "/logout":
            self.handle_logout(chat_id, cfg)
            return
        
        if text.startswith("🚀"):
            self.handle_queue(chat_id, cfg)
            return
        
        if text == "🗑️ مسح الانتظار":
            self.handle_clear_queue(chat_id, cfg)
            return
        
        if text == "🎨 تخصيص الهوية":
            self.handle_branding(chat_id, cfg)
            return
        
        if text == "📝 اسم السورس":
            self.handle_branding_name(chat_id, cfg)
            return
        
        if text == "👤 اسم المطور":
            self.handle_branding_dev(chat_id, cfg)
            return
        
        if text == "✋ اسم المسؤول":
            self.handle_branding_main(chat_id, cfg)
            return
        
        if text == "📄 وصف السورس":
            self.handle_branding_desc(chat_id, cfg)
            return
        
        if text == "🖼️ أيقونة السورس":
            self.handle_upload_image(chat_id, cfg)
            return
        
        if text == "📷 خلفية السورس":
            self.handle_upload_image(chat_id, cfg)
            return
        
        if text == "⚙️ إعدادات المستودع":
            self.handle_repo_settings(chat_id, cfg)
            return
        
        if text == "🔄 تغيير المستودع":
            self.handle_change_repo(chat_id, cfg)
            return
        
        if text == "🌿 تغيير الفرع":
            self.handle_change_branch(chat_id, cfg)
            return
        
        if text == "🔗 رابط السورس":
            self.handle_repo_url(chat_id, cfg)
            return
        
        if text == "📋 عرض الإعدادات":
            self.handle_show_settings(chat_id, cfg)
            return
        
        if text == "📊 حالة المستودع":
            self.handle_status(chat_id, cfg)
            return
        
        if text == "📦 رفع .deb":
            self.handle_upload_deb(chat_id, cfg)
            return
        
        if text == "🖼️ رفع صورة":
            self.handle_upload_image(chat_id, cfg)
            return
        
        if text == "🔙 رجوع":
            self.handle_back(chat_id, cfg)
            return
        
        # Handle text commands
        if text.startswith("/"):
            self.bot.send_message(
                chat_id,
                "❓ أمر غير معروف.\n"
                "استخدم الأزرار للتنقل.",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
            return
        
        # Handle branding text input (legacy format)
        if any(text.startswith(x) for x in ["Name:", "Dev:", "Main:", "Desc:"]):
            lines = text.split("\n")
            branding = cfg.get("branding", {})
            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    if "Name" in key:
                        branding["repo_name"] = value.strip()
                    if "Dev" in key:
                        branding["developer"] = value.strip()
                    if "Main" in key:
                        branding["maintainer"] = value.strip()
                    if "Desc" in key:
                        branding["description"] = value.strip()
            
            cfg["branding"] = branding
            config.save_user_config(chat_id, cfg)
            self.bot.send_message(
                chat_id,
                "✅ تم حفظ التعديلات.",
                reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
            )
            return
        
        # Default
        self.bot.send_message(
            chat_id,
            "❓ لم أفهم.\n"
            "استخدم الأزرار للتنقل.",
            reply_markup=keyboard.main_menu_keyboard(len(cfg.get("queue", [])))
        )
    
    def process_document(self, chat_id: int, document: dict) -> None:
        cfg = config.load_user_config(chat_id)
        self.handle_document(chat_id, document, cfg)
    
    def process_photo(self, chat_id: int, photos: list) -> None:
        cfg = config.load_user_config(chat_id)
        self.handle_photo(chat_id, photos, cfg)
