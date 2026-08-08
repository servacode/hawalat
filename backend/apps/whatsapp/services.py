"""خدمة الواتساب المركزية: قرار الوضع + الطابور."""

import re

from .models import WhatsAppMessage, WhatsAppSettings
from .tasks import send_whatsapp_message


def get_settings(tenant) -> WhatsAppSettings:
    obj, _ = WhatsAppSettings.all_objects.get_or_create(tenant=tenant)
    return obj


def _phone_chat_id(user) -> str:
    digits = re.sub(r"\D", "", user.phone or "")
    return f"{digits}@c.us" if digits else ""


def chat_id_for(user) -> str:
    """وجهة الإرسال للعضو (بلا شبكة): المعرّف المخزَّن، وإلا رقم هاتفه."""
    return user.whatsapp_chat_id or _phone_chat_id(user)


def _resolve_group_chat_id(to_user) -> str:
    """
    يستنتج معرّف المجموعة من رابط الدعوة عبر الخادم (ملاحظة 46) — والنتيجة
    تُخزَّن على العضو فلا يُسأل الخادم مرة أخرى. يشترط أن يكون الرقم
    المربوط عضواً في المجموعة ليستطيع الإرسال فيها.
    """
    match = re.search(r"chat\.whatsapp\.com/([A-Za-z0-9]+)", to_user.whatsapp_group_link or "")
    if not match:
        return ""
    from . import waha

    try:
        data = waha.group_join_info(to_user.tenant, match.group(1))
    except waha.WahaError:
        return ""
    gid = data.get("id", "")
    if isinstance(gid, dict):  # محرك WEBJS يعيد {id: {_serialized: "...@g.us"}}
        gid = gid.get("_serialized", "")
    gid = str(gid or "")
    if gid and "@" not in gid:
        gid = f"{gid}@g.us"
    if gid:
        to_user.whatsapp_chat_id = gid
        to_user.save(update_fields=["whatsapp_chat_id"])
    return gid


def bot_status(user) -> dict:
    """حالة البوت لهذا المستخدم: رقم مكتبه الكبير مربوط + له وجهة إرسال؟"""
    s = get_settings(user.tenant)
    return {
        "bot_enabled": s.is_ready,
        "chat_configured": bool(
            user.whatsapp_chat_id or user.whatsapp_group_link or _phone_chat_id(user)
        ),
    }


def queue_message(*, to_user, text: str) -> WhatsAppMessage | None:
    """
    يُدرج رسالة في الصادر ويطلق مهمة الإرسال — أو يعيد None إذا كان
    الوضع يدوياً (الرقم غير مربوط / لا وجهة للعضو).
    الوجهة بالأولوية: مجموعة العضو (معرّف مخزَّن أو مستنتَج من رابطها) ثم هاتفه.
    """
    s = get_settings(to_user.tenant)
    if not s.is_ready:
        return None
    chat_id = (
        to_user.whatsapp_chat_id or _resolve_group_chat_id(to_user) or _phone_chat_id(to_user)
    )
    if not chat_id:
        return None
    msg = WhatsAppMessage.all_objects.create(
        tenant=to_user.tenant,
        to_user=to_user,
        chat_id=chat_id,
        text=text,
    )
    # محاولة فورية ضمن الطلب (ملاحظة 47): لا اعتماد على عامل الخلفية —
    # وعند الفشل تُترك للطابور ليعيد المحاولة.
    from django.utils import timezone

    from .waha import WahaError, send_text

    try:
        send_text(to_user.tenant, chat_id, text)
    except WahaError as exc:
        msg.attempts = 1
        msg.last_error = str(exc)[:300]
        msg.save(update_fields=["attempts", "last_error"])
        send_whatsapp_message.delay(msg.pk)
    else:
        msg.status = WhatsAppMessage.Status.SENT
        msg.sent_at = timezone.now()
        msg.save(update_fields=["status", "sent_at"])
    return msg
