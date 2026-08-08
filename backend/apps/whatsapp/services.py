"""خدمة الواتساب المركزية: قرار الوضع + الطابور."""

import re

from .models import WhatsAppMessage, WhatsAppSettings
from .tasks import send_whatsapp_message


def get_settings(tenant) -> WhatsAppSettings:
    obj, _ = WhatsAppSettings.all_objects.get_or_create(tenant=tenant)
    return obj


def chat_id_for(user) -> str:
    """وجهة الإرسال للعضو: مجموعته إن ضُبطت، وإلا رقم هاتفه مباشرة (ملاحظة 44)."""
    if user.whatsapp_chat_id:
        return user.whatsapp_chat_id
    digits = re.sub(r"\D", "", user.phone or "")
    return f"{digits}@c.us" if digits else ""


def bot_status(user) -> dict:
    """حالة البوت لهذا المستخدم: رقم مكتبه الكبير مربوط + له وجهة إرسال؟"""
    s = get_settings(user.tenant)
    return {
        "bot_enabled": s.is_ready,
        "chat_configured": bool(chat_id_for(user)),
    }


def queue_message(*, to_user, text: str) -> WhatsAppMessage | None:
    """
    يُدرج رسالة في الصادر ويطلق مهمة الإرسال — أو يعيد None إذا كان
    الوضع يدوياً (الرقم غير مربوط / لا وجهة للعضو).
    """
    s = get_settings(to_user.tenant)
    chat_id = chat_id_for(to_user)
    if not s.is_ready or not chat_id:
        return None
    msg = WhatsAppMessage.all_objects.create(
        tenant=to_user.tenant,
        to_user=to_user,
        chat_id=chat_id,
        text=text,
    )
    send_whatsapp_message.delay(msg.pk)
    return msg
