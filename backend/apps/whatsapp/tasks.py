"""مهمة الإرسال الخلفية مع إعادة المحاولة (Celery)."""

from celery import shared_task
from django.utils import timezone

MAX_ATTEMPTS = 3


@shared_task(bind=True, max_retries=MAX_ATTEMPTS - 1, default_retry_delay=10)
def send_whatsapp_message(self, message_id: int):
    from .gateway import GatewayError, send_via_gateway
    from .models import WhatsAppMessage, WhatsAppSettings

    msg = WhatsAppMessage.all_objects.filter(pk=message_id).first()
    if msg is None or msg.status == WhatsAppMessage.Status.SENT:
        return
    settings_obj = WhatsAppSettings.all_objects.filter(tenant=msg.tenant).first()
    if settings_obj is None or not settings_obj.is_ready:
        msg.status = WhatsAppMessage.Status.FAILED
        msg.last_error = "البوت غير مفعّل أو البوابة غير مضبوطة."
        msg.save(update_fields=["status", "last_error"])
        return

    msg.attempts += 1
    try:
        send_via_gateway(
            gateway_url=settings_obj.gateway_url,
            token=settings_obj.gateway_token,
            chat_id=msg.chat_id,
            text=msg.text,
        )
    except GatewayError as exc:
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
