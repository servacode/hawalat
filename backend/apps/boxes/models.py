"""
حوالات — الصناديق والعملات والحدود (المرحلة 4)
==================================================
- Currency: عملات المستأجر — يديرها المكتب الكبير (الجزء 17).
- IntermediaryBox: صندوق وسيط (اسم + رقم + عملات متاحة) — الجزء 12.
- BoxCurrencyAccount / SmallOfficeAccount / ShopCashAccount: ربط كل كيان
  بحساب دفتر أستاذ لكل عملة (النواة تبقى عامة).
- CreditLimit: الحد السالب لكل (مكتب صغير × عملة) — الجزء 5.
"""

from django.conf import settings
from django.db import models

from apps.core.models import Account, Tenant, TenantScopedModel, TimeStampedModel


class Currency(TenantScopedModel):
    """عملة يعرّفها المكتب الكبير لمستأجره (سوري/تركي/دولار/يورو...)."""

    code = models.CharField("الرمز", max_length=8)  # USD/TRY/SYP/EUR
    name = models.CharField("الاسم", max_length=50)
    is_active = models.BooleanField("مفعّلة", default=True)

    class Meta:
        verbose_name = "عملة"
        verbose_name_plural = "العملات"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="uniq_currency_per_tenant")
        ]
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class IntermediaryBox(TenantScopedModel):
    """صندوق وسيط مالي: اسم + رقم + عملات متاحة (الجزء 12)."""

    name = models.CharField("اسم الصندوق", max_length=150)
    number = models.CharField("رقم الصندوق", max_length=50)
    currencies = models.ManyToManyField(
        Currency, verbose_name="العملات المتاحة", related_name="boxes"
    )
    is_active = models.BooleanField("مفعّل", default=True)

    class Meta:
        verbose_name = "صندوق وسيط"
        verbose_name_plural = "صناديق الوسطاء"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "number"], name="uniq_box_number_per_tenant")
        ]

    def __str__(self):
        return f"{self.name} #{self.number}"


class BoxCurrencyAccount(TenantScopedModel):
    """حساب دفتر الأستاذ لصندوق وسيط بعملة محددة."""

    box = models.ForeignKey(
        IntermediaryBox, on_delete=models.PROTECT, related_name="currency_accounts"
    )
    currency = models.CharField("العملة", max_length=8)
    account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name="box_link")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["box", "currency"], name="uniq_box_currency")
        ]

    def __str__(self):
        return f"{self.box} — {self.currency}"


class SmallOfficeAccount(TenantScopedModel):
    """حساب دفتر الأستاذ لمكتب صغير بعملة محددة."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="office_accounts",
    )
    currency = models.CharField("العملة", max_length=8)
    account = models.OneToOneField(
        Account, on_delete=models.PROTECT, related_name="small_office_link"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "currency"], name="uniq_small_office_currency")
        ]

    def __str__(self):
        return f"{self.user} — {self.currency}"


class ShopCashAccount(TenantScopedModel):
    """حساب صندوق المحل (النقد الفعلي) لكل عملة."""

    currency = models.CharField("العملة", max_length=8)
    account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name="shop_cash_link")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "currency"], name="uniq_shop_cash_currency")
        ]

    def __str__(self):
        return f"محل {self.tenant} — {self.currency}"


class CreditLimit(TenantScopedModel):
    """الحد السالب المسموح لمكتب صغير بعملة محددة (الجزء 5)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="المكتب الصغير",
        on_delete=models.PROTECT,
        related_name="credit_limits",
    )
    currency = models.CharField("العملة", max_length=8)
    # يُخزَّن موجباً: 5000 يعني يُسمح حتى −5000
    negative_limit = models.DecimalField(
        "الحد السالب المسموح", max_digits=18, decimal_places=4, default=0
    )

    class Meta:
        verbose_name = "حد سالب"
        verbose_name_plural = "الحدود السالبة"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "currency"], name="uniq_limit_per_user_currency"
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.currency}: −{self.negative_limit}"


# مرجع للاستيراد الموحّد
__all__ = [
    "Currency",
    "IntermediaryBox",
    "BoxCurrencyAccount",
    "SmallOfficeAccount",
    "ShopCashAccount",
    "CreditLimit",
    "Tenant",
    "TimeStampedModel",
]
