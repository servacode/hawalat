"""
حوالات — الإشعارات (آلية) والتنبيهات (بشرية) — الجزء 16 + 20-أ
==================================================================
- Notification: حدث يولّده النظام تلقائياً لمستلم محدد (جرس + شارة).
- OfficeBroadcast: تنبيه يدوي من المكتب الكبير إلى كل مكاتبه الصغيرة.
  (تنبيهات الأدمن للكبار في admin_panel.AdminBroadcast.)
"""

from django.conf import settings
from django.db import models

from apps.core.models import Tenant, TenantScopedModel, TimeStampedModel


class Notification(TimeStampedModel):
    """إشعار آلي لمستخدم — الأدمن بلا مستأجر لذا الحقل اختياري."""

    class Type(models.TextChoices):
        TXN_NEW = "txn_new", "حركة جديدة"
        TXN_ACCEPTED = "txn_accepted", "قبول حركة"
        TXN_REJECTED = "txn_rejected", "رفض حركة"
        TXN_PAID = "txn_paid", "قبض حركة"
        TXN_DELIVERED = "txn_delivered", "تسليم حركة"
        TXN_REVERSED = "txn_reversed", "عكس/تعديل حركة"
        SETTLEMENT = "settlement", "اعتماد/سحب"
        RECONCILIATION = "reconciliation", "مطابقة"
        LIMIT = "limit", "الحد السالب"
        SUBSCRIPTION = "subscription", "اشتراك"
        BROADCAST = "broadcast", "تنبيه"

    tenant = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="المستلم",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    ntype = models.CharField("النوع", max_length=24, choices=Type.choices)
    title = models.CharField("العنوان", max_length=200)
    body = models.CharField("النص", max_length=500, blank=True)
    entity = models.CharField("الكيان", max_length=64, blank=True)
    entity_id = models.CharField("معرّفه", max_length=64, blank=True)
    is_read = models.BooleanField("مقروء", default=False)

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.get_ntype_display()} → {self.recipient}"


class OfficeBroadcast(TenantScopedModel):
    """تنبيه يدوي: الكبير → كل مكاتبه الصغيرة (الجزء 16)."""

    title = models.CharField("العنوان", max_length=150)
    message = models.TextField("النص")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "تنبيه مكتب"
        verbose_name_plural = "تنبيهات المكاتب"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
