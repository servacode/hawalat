"""خدمة الواتساب المركزية: قرار الوضع + الطابور."""

from .models import WhatsAppMessage, WhatsAppSettings
from .tasks import send_whatsapp_message


def get_settings(tenant) -> WhatsAppSettings:
    obj, _ = WhatsAppSettings.all_objects.get_or_create(tenant=tenant)
    return obj


def bot_status(user) -> dict:
    """حالة البوت لهذا المستخدم: مفعّل لدى مستأجره + مجموعته مضبوطة؟"""
    s = get_settings(user.tenant)
    return {
        "bot_enabled": s.is_ready,
        "chat_configured": bool(user.whatsapp_chat_id),
    }


def queue_message(*, to_user, text: str) -> WhatsAppMessage | None:
    """
    يُدرج رسالة في الصادر ويطلق مهمة الإرسال — أو يعيد None إذا كان
    الوضع يدوياً (بوت مطفأ/بوابة غير مضبوطة/لا معرّف مجموعة).
    """
    s = get_settings(to_user.tenant)
    if not s.is_ready or not to_user.whatsapp_chat_id:
        return None
    msg = WhatsAppMessage.all_objects.create(
        tenant=to_user.tenant,
        to_user=to_user,
        chat_id=to_user.whatsapp_chat_id,
        text=text,
    )
    send_whatsapp_message.delay(msg.pk)
    return msg
