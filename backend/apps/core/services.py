"""
حوالات — خدمات محرك القيود المزدوجة (Ledger Engine)
======================================================
النقطة المركزية الوحيدة لإنشاء القيود. لا يُنشأ قيد من أي مكان آخر.

الضمانات (ق3):
- توازن إلزامي لكل عملة: مجموع المدين = مجموع الدائن.
- سطران على الأقل، والحسابات كلها لنفس المستأجر.
- عملة كل سطر = عملة حسابه (تُشتق منه ولا تُمرر يدوياً).
- العكس (reverse_entry) هو الطريق الوحيد للتصحيح — لا حذف.
"""

from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import JournalEntry, JournalLine

ZERO = Decimal("0")


@transaction.atomic
def post_entry(*, tenant, entry_type, lines, memo="", reverses=None):
    """
    ينشئ قيداً متوازناً.

    lines: قائمة عناصر (account, debit, credit) — Decimal حصراً.
    يعيد JournalEntry بعد التحقق الكامل.
    """
    if len(lines) < 2:
        raise ValidationError("القيد يحتاج سطرين على الأقل (قيد مزدوج).")

    totals = defaultdict(lambda: [ZERO, ZERO])  # currency -> [debit, credit]

    for account, debit, credit in lines:
        if account.tenant_id != tenant.id:
            raise ValidationError("كل حسابات القيد يجب أن تتبع نفس المستأجر.")
        if not isinstance(debit, Decimal) or not isinstance(credit, Decimal):
            raise ValidationError("المبالغ Decimal حصراً — لا floats في المال.")
        if debit < ZERO or credit < ZERO:
            raise ValidationError("لا مبالغ سالبة — الاتجاه يحدده المدين/الدائن.")
        if debit == ZERO and credit == ZERO:
            raise ValidationError("سطر بلا قيمة.")
        t = totals[account.currency]
        t[0] += debit
        t[1] += credit

    for currency, (d, c) in totals.items():
        if d != c:
            raise ValidationError(f"قيد غير متوازن بعملة {currency}: مدين {d} ≠ دائن {c}.")

    entry = JournalEntry.all_objects.create(
        tenant=tenant, entry_type=entry_type, memo=memo, reverses=reverses
    )
    JournalLine.all_objects.bulk_create(
        [
            JournalLine(tenant=tenant, entry=entry, account=acc, debit=debit, credit=credit)
            for acc, debit, credit in lines
        ]
    )
    return entry


@transaction.atomic
def reverse_entry(entry, memo=""):
    """يعكس قيداً قائماً: قيد مرآة يعيد كل الأرصدة — بديل الحذف الوحيد."""
    if hasattr(entry, "reversed_by"):
        raise ValidationError("هذا القيد معكوس مسبقاً.")
    mirror_lines = [
        (line.account, line.credit, line.debit)  # تبديل الطرفين
        for line in entry.lines.select_related("account")
    ]
    return post_entry(
        tenant=entry.tenant,
        entry_type=JournalEntry.EntryType.REVERSAL,
        lines=mirror_lines,
        memo=memo or f"عكس القيد #{entry.pk}",
        reverses=entry,
    )
