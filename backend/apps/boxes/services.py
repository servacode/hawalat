"""
حوالات — خدمات الصناديق والحسابات (المرحلة 4)
=================================================
النقطة المركزية لتوفير الحسابات، فرض الحد السالب، والتسويات (اعتماد/سحب).
كل القيود تمرّ حصراً عبر محرك القيود (core.services.post_entry).

الاصطلاح: balance = مدين − دائن.
- صغير: موجب = عليه. صندوق: موجب = رصيدنا فيه.
- اعتماد (المشهد 5): مدين الصندوق X / دائن الصغير X.
- سحب: مدين الصغير X / دائن الصندوق X.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.models import Account, JournalEntry
from apps.core.services import post_entry, reverse_entry

from .models import (
    BoxCurrencyAccount,
    CreditLimit,
    IntermediaryBox,
    ShopCashAccount,
    SmallOfficeAccount,
)

__all__ = ["reverse_entry"]

# ---------------------------------------------------------------- العملات الافتراضية

# العملات المتفق عليها (الجزء 17): تُزرع تلقائياً لكل مكتب كبير جديد،
# ويبقى المكتب حراً بإضافة غيرها أو تعطيلها.
DEFAULT_CURRENCIES = [
    ("USD", "دولار أمريكي"),
    ("EUR", "يورو"),
    ("TRY", "ليرة تركية"),
    ("SYP", "ليرة سورية"),
]


def seed_default_currencies(tenant) -> None:
    """يزرع العملات الافتراضية للمستأجر (idempotent — لا يكرر الموجود)."""
    from .models import Currency

    for code, name in DEFAULT_CURRENCIES:
        Currency.all_objects.get_or_create(tenant=tenant, code=code, defaults={"name": name})


# ---------------------------------------------------------------- توفير الحسابات


def get_small_office_account(user, currency: str) -> Account:
    """حساب المكتب الصغير بهذه العملة — يُنشأ عند أول حاجة."""
    link = SmallOfficeAccount.all_objects.filter(user=user, currency=currency).first()
    if link:
        return link.account
    with transaction.atomic():
        account = Account.all_objects.create(
            tenant=user.tenant,
            name=f"حساب {user.first_name or user.username}",
            kind=Account.Kind.SMALL_OFFICE,
            currency=currency,
        )
        SmallOfficeAccount.all_objects.create(
            tenant=user.tenant, user=user, currency=currency, account=account
        )
    return account


def get_box_account(box: IntermediaryBox, currency: str) -> Account:
    """حساب صندوق الوسيط بهذه العملة — العملة يجب أن تكون من عملات الصندوق."""
    if not box.currencies.filter(code=currency).exists():
        raise ValidationError(f"العملة {currency} غير متاحة في صندوق {box.name}.")
    link = BoxCurrencyAccount.all_objects.filter(box=box, currency=currency).first()
    if link:
        return link.account
    with transaction.atomic():
        account = Account.all_objects.create(
            tenant=box.tenant,
            name=f"وسيط {box.name} #{box.number}",
            kind=Account.Kind.INTERMEDIARY_BOX,
            currency=currency,
        )
        BoxCurrencyAccount.all_objects.create(
            tenant=box.tenant, box=box, currency=currency, account=account
        )
    return account


def get_shop_cash_account(tenant, currency: str) -> Account:
    link = ShopCashAccount.all_objects.filter(tenant=tenant, currency=currency).first()
    if link:
        return link.account
    with transaction.atomic():
        account = Account.all_objects.create(
            tenant=tenant,
            name="صندوق المحل",
            kind=Account.Kind.SHOP_CASH,
            currency=currency,
        )
        ShopCashAccount.all_objects.create(tenant=tenant, currency=currency, account=account)
    return account


def get_fees_profit_account(tenant, currency: str) -> Account:
    account, _ = Account.all_objects.get_or_create(
        tenant=tenant,
        name="أرباح الأجور",
        kind=Account.Kind.FEES_PROFIT,
        currency=currency,
    )
    return account


# ---------------------------------------------------------------- الحد السالب


def get_negative_limit(user, currency: str) -> Decimal:
    limit = CreditLimit.all_objects.filter(user=user, currency=currency).first()
    return limit.negative_limit if limit else Decimal("0")


def check_credit_limit(user, currency: str, additional_debit: Decimal) -> tuple[bool, str]:
    """
    هل يستطيع المكتب الصغير تحمّل دين إضافي بهذه العملة؟ (الجزء 5)

    الرصيد موجب = عليه. الحد −L يعني: أقصى ما يُسمح أن يبلغه «عليه» هو L.
    ملاحظة اتجاه: «عليه» في دفاترنا يقابل رصيده هو بالسالب — لذا شرط السماح:
        (عليه الحالي + الإضافة) ≤ الحد المسموح L
    """
    limit = get_negative_limit(user, currency)
    account = get_small_office_account(user, currency)
    owed_after = account.balance + additional_debit  # موجب = عليه
    if owed_after > limit:
        return False, (f"تجاوزت الحد المسموح ({limit} {currency}) — يرجى تعزيز الرصيد.")
    return True, ""


# ---------------------------------------------------------------- التسويات (المشهد 5)


def deposit_to_box(
    *, tenant, box: IntermediaryBox, small_user, currency: str, amount: Decimal, memo: str = ""
):
    """اعتماد: يُسجَّل باسم المكتب الصغير — يزيد الصندوق ويُنقص ما على الصغير."""
    if amount <= 0:
        raise ValidationError("مبلغ الاعتماد يجب أن يكون موجباً.")
    box_account = get_box_account(box, currency)
    small_account = get_small_office_account(small_user, currency)
    return post_entry(
        tenant=tenant,
        entry_type=JournalEntry.EntryType.SETTLEMENT,
        memo=f"اعتماد باسم {small_user.first_name or small_user.username}: "
        f"في صندوق {box.name}" + (f" — {memo}" if memo else ""),
        lines=[
            (box_account, amount, Decimal("0")),  # مدين: زاد رصيدنا في الصندوق
            (small_account, Decimal("0"), amount),  # دائن: نقص ما على الصغير
        ],
    )


def withdraw_from_box(
    *, tenant, box: IntermediaryBox, small_user, currency: str, amount: Decimal, memo: str = ""
):
    """سحب: عكس الاعتماد — ينقص الصندوق ويزيد ما على الصغير."""
    if amount <= 0:
        raise ValidationError("مبلغ السحب يجب أن يكون موجباً.")
    box_account = get_box_account(box, currency)
    small_account = get_small_office_account(small_user, currency)
    return post_entry(
        tenant=tenant,
        entry_type=JournalEntry.EntryType.SETTLEMENT,
        memo=f"سحب باسم {small_user.first_name or small_user.username}: "
        f"من صندوق {box.name}" + (f" — {memo}" if memo else ""),
        lines=[
            (small_account, amount, Decimal("0")),  # مدين: زاد ما على الصغير
            (box_account, Decimal("0"), amount),  # دائن: نقص الصندوق
        ],
    )


def adjust_box(*, tenant, box: IntermediaryBox, currency: str, amount: Decimal, direction: str, reason: str):
    """
    تسوية صندوق (ملاحظة 16): تصحيح رصيد سابق أو فرق جرد — بسبب واضح إلزامي.
    direction: "in" يزيد رصيدنا في الصندوق، "out" ينقصه. الطرف المقابل حساب «تسويات الصناديق».
    """
    if amount <= 0:
        raise ValidationError("مبلغ التسوية يجب أن يكون موجباً.")
    if direction not in ("in", "out"):
        raise ValidationError("اتجاه التسوية غير صالح.")
    if not (reason or "").strip():
        raise ValidationError("سبب التسوية إلزامي.")
    box_account = get_box_account(box, currency)
    adj_account, _ = Account.all_objects.get_or_create(
        tenant=tenant,
        name="تسويات الصناديق",
        kind=Account.Kind.ADJUSTMENT,
        currency=currency,
    )
    label = "إضافة" if direction == "in" else "خصم"
    lines = (
        [(box_account, amount, Decimal("0")), (adj_account, Decimal("0"), amount)]
        if direction == "in"
        else [(adj_account, amount, Decimal("0")), (box_account, Decimal("0"), amount)]
    )
    return post_entry(
        tenant=tenant,
        entry_type=JournalEntry.EntryType.SETTLEMENT,
        memo=f"تسوية {label}: {reason.strip()}",
        lines=lines,
    )


# ---------------------------------------------------------------- كشوف


# تصنيف سطر الكشف (ملاحظة 22): نوع واضح + بيان نظيف (مرجع أو ملاحظة)
import re as _re

_REF_RE = _re.compile(r"HW-[A-Z0-9-]*\d")

STATEMENT_KIND_LABELS = {
    "transaction": "حوالة",
    "deposit": "اعتماد",
    "withdraw": "سحب",
    "payment": "قبض",
    "reversal": "عكس/ملغاة",
    "adjustment": "تسوية",
    "settlement": "تسوية",
}


def classify_statement_line(entry_type: str, memo: str) -> tuple[str, str]:
    """يعيد (kind, note): النوع المصنّف والبيان النظيف — المرجع إن وُجد وإلا الملاحظة."""
    memo = memo or ""
    if entry_type == JournalEntry.EntryType.REVERSAL:
        kind = "reversal"
    elif entry_type == JournalEntry.EntryType.TRANSACTION:
        kind = "transaction"
    elif memo.startswith("اعتماد"):
        kind = "deposit"
    elif memo.startswith("سحب"):
        kind = "withdraw"
    elif memo.startswith("قبض"):
        kind = "payment"
    elif memo.startswith("تسوية"):
        kind = "adjustment"
    else:
        kind = "settlement"
    m = _REF_RE.search(memo)
    if m:
        note = m.group(0)
    elif ":" in memo:
        note = memo.split(":", 1)[1].strip()
    else:
        note = memo
    return kind, note


def account_statement(account: Account, limit: int = 200):
    """كشف حساب: الأسطر الأخيرة مع الرصيد الجاري."""
    lines = account.lines.select_related("entry").order_by("-created_at", "-id")[:limit]
    return {
        "account": account,
        "balance": account.balance,
        "display_balance": account.display_balance,
        "lines": [
            {
                "id": line.id,
                "entry_id": line.entry_id,
                "entry_type": line.entry.entry_type,
                "memo": line.entry.memo,
                "kind": (c := classify_statement_line(line.entry.entry_type, line.entry.memo))[0],
                "note": c[1],
                "debit": line.debit,
                "credit": line.credit,
                "at": line.created_at,
            }
            for line in lines
        ],
    }


# ---------------------------------------------------------------- المطابقة (المشهد 4)


def build_reconciliation(user):
    """
    يبني كشف المطابقة الحالي لمكتب صغير:
    لكل عملة: الرصيد السابق (آخر مطابقة) + مدين/دائن الفترة + الرصيد الحالي.
    ثابت داخلي: السابق + مدين − دائن = الرصيد الفعلي للحساب (يُختبر آلياً).
    """
    from .models import Reconciliation

    last = Reconciliation.all_objects.filter(user=user).order_by("-created_at").first()
    since = last.created_at if last else None
    prev_map = {row["currency"]: Decimal(row["balance"]) for row in last.snapshot} if last else {}

    rows = []
    links = SmallOfficeAccount.all_objects.filter(user=user).select_related("account")
    for link in links:
        account = link.account
        qs = account.lines.all()
        if since:
            qs = qs.filter(created_at__gt=since)
        from django.db.models import Sum

        agg = qs.aggregate(debit=Sum("debit", default=0), credit=Sum("credit", default=0))
        previous = prev_map.get(link.currency, Decimal("0"))
        balance = previous + agg["debit"] - agg["credit"]
        rows.append(
            {
                "currency": link.currency,
                "previous": str(previous),
                "debits": str(agg["debit"]),
                "credits": str(agg["credit"]),
                "balance": str(balance),  # موجب = عليه، سالب = له
            }
        )
    return {"last_at": since, "rows": rows}


def commit_reconciliation(user, *, created_by):
    """يثبّت المطابقة: يحفظ اللقطة فتصبح نقطة الإغلاق الجديدة."""
    from .models import Reconciliation

    data = build_reconciliation(user)
    # اللقطة الكاملة (سابق/مدين/دائن/رصيد) — سجل يُرجع إليه عند أي خلاف (ملاحظة 12)
    rec = Reconciliation.all_objects.create(
        tenant=user.tenant,
        user=user,
        created_by=created_by,
        snapshot=[
            {
                "currency": r["currency"],
                "previous": r["previous"],
                "debits": r["debits"],
                "credits": r["credits"],
                "balance": r["balance"],
            }
            for r in data["rows"]
        ],
    )
    return rec, data
