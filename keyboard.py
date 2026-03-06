from typing import List, Dict, Any

def main_menu_keyboard(queue_size: int = 0) -> Dict[str, Any]:
    queue_text = f"🚀 رفع الانتظار ({queue_size})" if queue_size > 0 else "🚀 رفع التحديثات"
    
    return {
        "keyboard": [
            [{"text": queue_text}, {"text": "🗑️ مسح الانتظار"}],
            [{"text": "📦 رفع .deb"}, {"text": "🖼️ رفع صورة"}],
            [{"text": "🎨 تخصيص الهوية"}, {"text": "⚙️ إعدادات المستودع"}],
            [{"text": "📊 حالة المستودع"}, {"text": "🚪 خروج"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def branding_menu_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "📝 اسم السورس"}, {"text": "👤 اسم المطور"}],
            [{"text": "✋ اسم المسؤول"}, {"text": "📄 وصف السورس"}],
            [{"text": "🖼️ أيقونة السورس"}, {"text": "📷 خلفية السورس"}],
            [{"text": "🔙 رجوع"}]
        ],
        "resize_keyboard": True
    }

def repo_settings_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "🔄 تغيير المستودع"}, {"text": "🌿 تغيير الفرع"}],
            [{"text": "🔗 رابط السورس"}, {"text": "📋 عرض الإعدادات"}],
            [{"text": "🔙 رجوع"}]
        ],
        "resize_keyboard": True
    }

def cancel_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "❌ إلغاء"}]
        ],
        "resize_keyboard": True
    }

def remove_keyboard() -> Dict[str, Any]:
    return {"remove_keyboard": True}

def yes_no_keyboard() -> Dict[str, Any]:
    return {
        "keyboard": [
            [{"text": "✅ نعم"}, {"text": "❌ لا"}]
        ],
        "resize_keyboard": True
    }

def build_button_rows(buttons: List[str], cols: int = 2) -> List[List[Dict[str, str]]]:
    rows = []
    for i in range(0, len(buttons), cols):
        row = [{"text": btn} for btn in buttons[i:i+cols]]
        rows.append(row)
    return rows
