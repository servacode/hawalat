"""
حوالات — تكامل الواتساب (الجزء 17 §6)
=========================================
- الوضع الافتراضي: رابط يدوي (خصوصية — لا ربط لرقم المكتب).
- ميزة «بوت» اختيارية بمفتاح لكل مستأجر: مفعّلة → إرسال تلقائي عبر بوابة
  HTTP عامة (متوافقة مع بوابات مثل WAHA)؛ مطفأة → يدوي بالرابط.
- Outbox: كل رسالة بوت تُسجَّل بحالة (قيد الإرسال/أُرسلت/فشلت) مع إعادة محاولة.
"""

from django.conf import settings
from django.db import models

from apps.core.models import TenantScopedModel


class WhatsAppSettings(TenantScopedModel):
    """إعدادات واتساب المستأجر — يتحكم بها المكتب الكبير حصراً."""

    bot_enabled = models.BooleanField("البوت مفعّل", default=False)
    gateway_url = models.URLField("عنوان البوابة", blank=True)
    gateway_token = models.CharField("رمز البوابة", max_length=255, blank=True)

    class Meta:
        verbose_name = "إعدادات واتساب"
        verbose_name_plural = "إعدادات واتساب"
        constraints = [
            models.UniqueConstraint(fields=["tenant"], name="uniq_wa_settings_per_tenant")
        ]

    def __str__(self):
        return f"واتساب {self.tenant} — بوت {'✓' if self.bot_enabled else '✗'}"

    @property
    def is_ready(self) -> bool:
        return self.bot_enabled and bool(self.gateway_url)


class WhatsAppMessage(TenantScopedModel):
    """رسالة صادرة عبر البوت (Outbox) — تتبّع كامل مع إعادة المحاولة."""

    class Status(models.TextChoices):
        PENDING = "pending", "قيد الإرسال"
        SENT = "sent", "أُرسلت"
        FAILED = "failed", "فشلت"

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="لمجموعة المكتب",
        on_delete=models.CASCADE,
        related_name="whatsapp_messages",
    )
    chat_id = models.CharField("معرّف المحادثة", max_length=100)
    text = models.TextField("النص")
    status = models.CharField(
        "الحالة", max_length=12, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveSmallIntegerField("محاولات", default=0)
    last_error = models.CharField("آخر خطأ", max_length=300, blank=True)
    sent_at = models.DateTimeField("أُرسلت في", null=True, blank=True)

    class Meta:
        verbose_name = "رسالة واتساب"
        verbose_name_plural = "رسائل الواتساب"
        ordering = ["-created_at"]

    def __str__(self):
        return f"→ {self.chat_id} [{self.get_status_display()}]"
