"""مهمة الإرسال الخلفية مع إعادة المحاولة (Celery)."""

from celery import shared_task
from django.utils import timezone

MAX_ATTEMPTS = 3


@shared_task
def waha_keepalive():
    """يُبقي خادم الواتساب المجاني مستيقظاً (ملاحظة 48) — نبضة كل 10 دقائق."""
    import requests

    from apps.core.models import PlatformSettings

    p = PlatformSettings.load()
    if not p.waha_url:
        return
    try:
        requests.get(p.waha_url.rstrip("/") + "/ping", timeout=10)
    except requests.RequestException:
        pass


def deliver_once(message_id: int) -> bool:
    """
    محاولة تسليم واحدة (بلا Celery): True = انتهت (أُرسلت أو فشلت نهائياً)،
    False = فشلت مؤقتاً وتستحق إعادة محاولة.
    """
    from .models import WhatsAppMessage, WhatsAppSettings
    from .waha import WahaError, send_text

    msg = WhatsAppMessage.all_objects.filter(pk=message_id).first()
    if msg is None or msg.status == WhatsAppMessage.Status.SENT:
        return True
    settings_obj = WhatsAppSettings.all_objects.filter(tenant=msg.tenant).first()
    if settings_obj is None or not settings_obj.is_ready:
        msg.status = WhatsAppMessage.Status.FAILED
        msg.last_error = "رقم الواتساب غير مربوط."
        msg.save(update_fields=["status", "last_error"])
        return True

    msg.attempts += 1
    try:
        send_text(msg.tenant, msg.chat_id, msg.text)
    except WahaError as exc:
        msg.last_error = str(exc)[:300]
        if msg.attempts >= MAX_ATTEMPTS:
            msg.status = WhatsAppMessage.Status.FAILED
            msg.save(update_fields=["attempts", "last_error", "status"])
            return True
        msg.save(update_fields=["attempts", "last_error"])
        return False
    msg.status = WhatsAppMessage.Status.SENT
    msg.sent_at = timezone.now()
    msg.last_error = ""
    msg.save(update_fields=["attempts", "status", "sent_at", "last_error"])
    return True


def retry_in_thread(message_id: int):
    """
    إعادة محاولة مضمونة بلا أي بنية خلفية (ملاحظة 49): خيط بسيط يعيد
    التسليم بعد 45 ثم 60 ثانية — تكفي «صحوة» الخادم المجاني النائم.
    (deliver_once تتجاهل الرسالة إن كانت أُرسلت — فلا ازدواج مع Celery.)
    """
    import threading
    import time

    def _run():
        for delay in (45, 60):
            time.sleep(delay)
            if deliver_once(message_id):
                return

    threading.Thread(target=_run, daemon=True).start()


@shared_task(bind=True, max_retries=MAX_ATTEMPTS - 1, default_retry_delay=30)
def send_whatsapp_message(self, message_id: int):
    from .models import WhatsAppMessage

    if not deliver_once(message_id):
        msg = WhatsAppMessage.all_objects.filter(pk=message_id).first()
        raise self.retry(exc=Exception(msg.last_error if msg else "فشل الإرسال"))
