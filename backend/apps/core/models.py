"""
حوالات — نماذج النواة المركزية
=================================
- TimeStampedModel: طوابع زمنية موحّدة.
- Tenant: سجل المستأجرين (كل مكتب كبير = مستأجر).
- TenantScopedModel: أساس كل نموذج مالي (عزل ق2).
- Account / JournalEntry / JournalLine: هيكل محرك القيود المزدوجة (ق3).
- AuditLog: سجل التدقيق (من فعل ماذا ومتى).

قواعد صارمة:
- المال Decimal فقط (ق3) — لا floats إطلاقاً.
- لا حذف لقيود اليومية — التصحيح بعكس القيد (ق3).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .tenancy import TenantManager, get_current_tenant

# ---------------------------------------------------------------- الأساسات


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("أُنشئ في", auto_now_add=True)
    updated_at = models.DateTimeField("عُدّل في", auto_now=True)

    class Meta:
        abstract = True


class Tenant(TimeStampedModel):
    """المستأجر = مكتب كبير. البيانات المالية كلها معزولة تحته."""

    name = models.CharField("الاسم", max_length=150)
    code = models.CharField("الكود الفريد", max_length=20, unique=True)
    is_active = models.BooleanField("نشط", default=True)
    # صلاحية يمنحها الكبير من إعداداته (ملاحظة التجربة 10): افتراضياً ممنوعة
    allow_small_reconciliation = models.BooleanField(
        "السماح للمكاتب الصغيرة بتثبيت المطابقة وإرسالها", default=False
    )

    class Meta:
        verbose_name = "مستأجر (مكتب كبير)"
        verbose_name_plural = "المستأجرون (المكاتب الكبيرة)"

    def __str__(self):
        return f"{self.name} [{self.code}]"


class TenantScopedModel(TimeStampedModel):
    """أساس كل نموذج مالي: يحمل المستأجر ويُفلتر تلقائياً بالسياق الحالي."""

    tenant = models.ForeignKey(
        Tenant,
        verbose_name="المستأجر",
        on_delete=models.PROTECT,
        related_name="+",
    )

    objects = TenantManager()
    all_objects = models.Manager()  # noqa: DJ012 — غير مفلتر، استخدام واعٍ فقط

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # إسناد تلقائي للمستأجر من السياق إن لم يُحدد صراحةً
        if self.tenant_id is None:
            tenant = get_current_tenant()
            if tenant is not None:
                self.tenant = tenant
        super().save(*args, **kwargs)


# ---------------------------------------------------------------- محرك القيود (هيكل)


class Account(TenantScopedModel):
    """
    حساب في دفتر الأستاذ — لكل (كيان × عملة) حساب واحد.

    اصطلاح الرصيد (مضبوط على سرد الدورة التشغيلية):
        balance = مجموع المدين − مجموع الدائن  (debit − credit)

    الدلالة حسب نوع الحساب:
    - حساب مكتب صغير:  موجب = «عليه» (مدين لنا)، سالب = «له».
    - صندوق وسيط/محل:  موجب = رصيدنا الموجود فيه، سالب = «علينا له».
      (الاعتماد/الإيداع يزيده، وتمرير الحركة ينقصه — كما في المشهدين 2 و5.)
    - حساب أرباح الأجور (دخل): يتراكم دائناً — يُعرض في التقارير معكوساً
      (credit − debit) ليظهر الربح موجباً.
    """

    class Kind(models.TextChoices):
        SMALL_OFFICE = "small_office", "حساب مكتب صغير"
        INTERMEDIARY_BOX = "intermediary_box", "صندوق وسيط مالي"
        SHOP_CASH = "shop_cash", "صندوق المحل (نقد)"
        SELF = "self", "الحساب الذاتي للمكتب الكبير"
        FEES_PROFIT = "fees_profit", "أرباح الأجور"
        FX_CLEARING = "fx_clearing", "مقاصة صرف العملات"

    name = models.CharField("الاسم", max_length=150)
    kind = models.CharField("النوع", max_length=32, choices=Kind.choices)
    currency = models.CharField("العملة", max_length=8)  # USD/TRY/SYP/EUR...

    class Meta:
        verbose_name = "حساب"
        verbose_name_plural = "الحسابات"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name", "kind", "currency"],
                name="uniq_account_per_tenant",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.currency})"

    @property
    def balance(self):
        agg = self.lines.aggregate(
            debit=models.Sum("debit", default=0),
            credit=models.Sum("credit", default=0),
        )
        return agg["debit"] - agg["credit"]

    @property
    def display_balance(self):
        """رصيد العرض: حسابات الدخل (الأرباح) تُعرض معكوسة لتظهر موجبة."""
        if self.kind == self.Kind.FEES_PROFIT:
            return -self.balance
        return self.balance


class JournalEntry(TenantScopedModel):
    """قيد يومية — مجموعة أسطر متوازنة. لا يُحذف أبداً (ق3)."""

    class EntryType(models.TextChoices):
        TRANSACTION = "transaction", "حركة (حوالة)"
        SETTLEMENT = "settlement", "تسوية (اعتماد/سحب/دفعة)"
        REVERSAL = "reversal", "عكس قيد"
        MANUAL = "manual", "يدوي"

    entry_type = models.CharField("نوع القيد", max_length=20, choices=EntryType.choices)
    memo = models.CharField("البيان", max_length=255, blank=True)
    reverses = models.OneToOneField(
        "self",
        verbose_name="يعكس القيد",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversed_by",
    )

    class Meta:
        verbose_name = "قيد يومية"
        verbose_name_plural = "قيود اليومية"

    def __str__(self):
        return f"قيد #{self.pk} — {self.get_entry_type_display()}"

    def delete(self, *args, **kwargs):
        raise ValidationError("لا يجوز حذف قيود اليومية — استخدم عكس القيد (Reversal).")


class JournalLine(TenantScopedModel):
    """سطر قيد: مدين أو دائن على حساب واحد وبعملة الحساب نفسها."""

    entry = models.ForeignKey(
        JournalEntry,
        verbose_name="القيد",
        on_delete=models.PROTECT,
        related_name="lines",
    )
    account = models.ForeignKey(
        Account, verbose_name="الحساب", on_delete=models.PROTECT, related_name="lines"
    )
    # المال Decimal حصراً (ق3): 18 خانة، 4 منازل عشرية
    debit = models.DecimalField("مدين", max_digits=18, decimal_places=4, default=0)
    credit = models.DecimalField("دائن", max_digits=18, decimal_places=4, default=0)

    class Meta:
        verbose_name = "سطر قيد"
        verbose_name_plural = "أسطر القيود"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(debit__gte=0) & models.Q(credit__gte=0) & ~models.Q(debit=0, credit=0)
                ),
                name="line_nonnegative_and_nonzero",
            )
        ]

    def __str__(self):
        return f"سطر {self.account} — مدين {self.debit} / دائن {self.credit}"

    def delete(self, *args, **kwargs):
        raise ValidationError("لا يجوز حذف أسطر القيود — استخدم عكس القيد.")


# ---------------------------------------------------------------- سجل التدقيق


class AuditLog(TimeStampedModel):
    """من فعل ماذا ومتى — يشمل أفعال الأدمن (بلا مستأجر) وأفعال المكاتب."""

    tenant = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="الفاعل",
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    action = models.CharField("الفعل", max_length=64)  # approve/reject/edit/block...
    entity = models.CharField("الكيان", max_length=64)
    entity_id = models.CharField("معرّف الكيان", max_length=64, blank=True)
    data = models.JSONField("بيانات إضافية", default=dict, blank=True)

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.entity}#{self.entity_id}"


# ---------------------------------------------------------------- إعدادات المنصة


class PlatformSettings(TimeStampedModel):
    """
    إعدادات المنصة العامة (صف واحد) — يتحكم بها الأدمن حصراً.

    - free_mode: الوضع المجاني (الجزء 18) — كل شيء مفتوح بلا باقات.
    - self_registration_enabled: مفتاح التسجيل الذاتي للمكاتب الكبيرة
      (المشهد 6: الزر موجود لكنه معطّل افتراضياً).
    """

    free_mode = models.BooleanField("الوضع المجاني", default=True)
    self_registration_enabled = models.BooleanField("التسجيل الذاتي مفعّل", default=False)

    class Meta:
        verbose_name = "إعدادات المنصة"
        verbose_name_plural = "إعدادات المنصة"

    def __str__(self):
        return "إعدادات المنصة"

    @classmethod
    def load(cls) -> "PlatformSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
