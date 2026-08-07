"""
حوالات — نماذج لوحة الأدمن: الباقات والاشتراكات وبث التنبيهات
=================================================================
(الجزء 18 + المشهد 1)
- Package: حدّان (عدد المكاتب الصغيرة + عدد الحركات) + سعر + مدة.
- Subscription: طلب → دفع يدوي خارج النظام → تفعيل الأدمن.
- قاعدة الترحيل (Grandfathering): ما أُنشئ قبل التفعيل لا يُحتسب على الحد.
- AdminBroadcast: تنبيهات الأدمن للمكاتب الكبيرة فقط (الجزء 16).
"""

from django.conf import settings
from django.db import models

from apps.core.models import Tenant, TimeStampedModel


class Package(TimeStampedModel):
    """باقة اشتراك يعرّفها الأدمن."""

    name = models.CharField("الاسم", max_length=100, unique=True)
    max_small_offices = models.PositiveIntegerField("حد المكاتب الصغيرة")
    max_transactions = models.PositiveIntegerField("حد الحركات")
    price = models.DecimalField("السعر", max_digits=12, decimal_places=2)
    currency = models.CharField("عملة السعر", max_length=8, default="USD")
    duration_days = models.PositiveIntegerField("المدة بالأيام", default=30)
    is_active = models.BooleanField("متاحة للطلب", default=True)

    class Meta:
        verbose_name = "باقة"
        verbose_name_plural = "الباقات"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} ({self.max_small_offices} مكتب / {self.max_transactions} حركة)"


class Subscription(TimeStampedModel):
    """اشتراك مكتب كبير في باقة — الدفع يدوي والتفعيل من الأدمن حصراً."""

    class Status(models.TextChoices):
        PENDING = "pending", "بانتظار التفعيل"
        ACTIVE = "active", "مفعّل"
        EXPIRED = "expired", "منتهٍ"
        REJECTED = "rejected", "مرفوض"

    tenant = models.ForeignKey(
        Tenant, verbose_name="المكتب الكبير", on_delete=models.PROTECT, related_name="subscriptions"
    )
    package = models.ForeignKey(
        Package, verbose_name="الباقة", on_delete=models.PROTECT, related_name="subscriptions"
    )
    status = models.CharField(
        "الحالة", max_length=16, choices=Status.choices, default=Status.PENDING
    )
    requested_at = models.DateTimeField("تاريخ الطلب", auto_now_add=True)
    activated_at = models.DateTimeField("تاريخ التفعيل", null=True, blank=True)
    expires_at = models.DateTimeField("تاريخ الانتهاء", null=True, blank=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="فعّله",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    note = models.CharField("ملاحظة", max_length=255, blank=True)

    class Meta:
        verbose_name = "اشتراك"
        verbose_name_plural = "الاشتراكات"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.tenant} ← {self.package} [{self.get_status_display()}]"


class AdminBroadcast(TimeStampedModel):
    """تنبيه يدوي من الأدمن إلى كل المكاتب الكبيرة (لا علاقة له بالصغار)."""

    title = models.CharField("العنوان", max_length=150)
    message = models.TextField("النص")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="أرسله",
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "تنبيه أدمن"
        verbose_name_plural = "تنبيهات الأدمن"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
