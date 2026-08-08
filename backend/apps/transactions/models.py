"""
حوالات — نموذج الحركة (الحوالة) — المرحلة 5
==============================================
الحقول من الأجزاء 3/4/8/17 والمشهد 2:
- مرسِل/مستفيد/مبلغ/وجهة (نص حر)/عملة مقبوضة/عملة مسلَّمة/سعر صرف.
- رقم مرجعي فريد مرتبط بكود المكتب: HW-BIG001-000001.
- الأجور: رأس المال (تكلفة الوسيط) والمستحقة (على الصغير) — بالعملة المقبوضة.
- ثلاث حالات مستقلة: قبول/دفع/تسليم. لا حذف — عكس قيد فقط.
"""

from django.conf import settings
from django.db import models

from apps.boxes.models import IntermediaryBox
from apps.core.models import JournalEntry, TenantScopedModel


class Transaction(TenantScopedModel):
    class Approval(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        ACCEPTED = "accepted", "مقبولة"
        CANCELLED = "cancelled", "ملغية"
        REVERSED = "reversed", "معكوسة"

    class Payment(models.TextChoices):
        UNPAID = "unpaid", "غير مدفوعة"
        PAID = "paid", "مدفوعة"

    class Delivery(models.TextChoices):
        NOT_DELIVERED = "not_delivered", "لم تُسلَّم"
        DELIVERED = "delivered", "تم التسليم"

    reference_code = models.CharField("الرقم المرجعي", max_length=40)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="أنشأها",
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    sender = models.CharField("اسم المرسِل", max_length=150, blank=True, default="")
    beneficiary = models.CharField("اسم المستفيد", max_length=150)
    destination = models.CharField("الوجهة", max_length=150)  # نص حر (الجزء 17)

    amount = models.DecimalField("المبلغ (بالمقبوضة)", max_digits=18, decimal_places=4)
    currency_received = models.CharField("العملة المقبوضة", max_length=8)
    currency_delivered = models.CharField("العملة المسلَّمة", max_length=8)
    exchange_rate = models.DecimalField(
        "سعر الصرف", max_digits=18, decimal_places=6, null=True, blank=True
    )
    amount_delivered = models.DecimalField(
        "المبلغ المسلَّم", max_digits=18, decimal_places=4, null=True, blank=True
    )

    # الأجور بالعملة المقبوضة (قرار تقني موثّق — الدورة §8)
    fee_cost = models.DecimalField(
        "رأس مال الأجور", max_digits=18, decimal_places=4, null=True, blank=True
    )
    fee_charged = models.DecimalField(
        "الأجور المستحقة", max_digits=18, decimal_places=4, null=True, blank=True
    )

    box = models.ForeignKey(
        IntermediaryBox,
        verbose_name="صندوق الوسيط",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    approval_status = models.CharField(
        "حالة القبول", max_length=16, choices=Approval.choices, default=Approval.PENDING
    )
    payment_status = models.CharField(
        "حالة الدفع", max_length=16, choices=Payment.choices, default=Payment.UNPAID
    )
    delivery_status = models.CharField(
        "حالة التسليم",
        max_length=16,
        choices=Delivery.choices,
        default=Delivery.NOT_DELIVERED,
    )

    approval_entry = models.ForeignKey(
        JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    payment_entry = models.ForeignKey(
        JournalEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    approved_at = models.DateTimeField("تاريخ القبول", null=True, blank=True)

    class Meta:
        verbose_name = "حركة"
        verbose_name_plural = "الحركات"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "reference_code"], name="uniq_reference_per_tenant"
            )
        ]

    def __str__(self):
        return f"{self.reference_code} — {self.sender} → {self.beneficiary}"

    @property
    def is_dual_currency(self):
        return self.currency_received != self.currency_delivered
