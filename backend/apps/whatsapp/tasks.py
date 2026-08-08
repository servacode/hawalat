"""مهمة الإرسال الخلفية مع إعادة المحاولة (Celery)."""

from celery import shared_task
from django.utils import timezone

MAX_ATTEMPTS = 3


@shared_task(bind=True, max_retries=MAX_ATTEMPTS - 1, default_retry_delay=10)
def send_whatsapp_message(self, message_id: int):
    from .models import WhatsAppMessage, WhatsAppSettings
    from .waha import WahaError, send_text

    msg = WhatsAppMessage.all_objects.filter(pk=message_id).first()
    if msg is None or msg.status == WhatsAppMessage.Status.SENT:
        return
    settings_obj = WhatsAppSettings.all_objects.filter(tenant=msg.tenant).first()
    if settings_obj is None or not settings_obj.is_ready:
        msg.status = WhatsAppMessage.Status.FAILED
        msg.last_error = "رقم الواتساب غير مربوط."
        msg.save(update_fields=["status", "last_error"])
        return

    msg.attempts += 1
    try:
        send_text(msg.tenant, msg.chat_id, msg.text)
    except WahaError as exc:
        msg.last_error = str(exc)[:300]
        if msg.attempts >= MAX_ATTEMPTS:
            msg.status = WhatsAppMessage.Status.FAILED
            msg.save(update_fields=["attempts", "last_error", "status"])
            return
        msg.save(update_fields=["attempts", "last_error"])
        raise self.retry(exc=exc) from exc
    msg.status = WhatsAppMessage.Status.SENT
    msg.sent_at = timezone.now()
    msg.last_error = ""
    msg.save(update_fields=["attempts", "status", "sent_at", "last_error"])
