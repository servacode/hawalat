"""
حوالات — بُناة التقارير الـ13 (الجزء 20)
=============================================
كل تقرير دالة تُرجع {title, columns, rows} — نفس البنية تُعرض في الواجهة
وتُصدَّر Excel/PDF. كلها معزولة بالمستأجر (TenantManager) ومفلترة بالتاريخ.

الأرقام تُعاد كنصوص Decimal — التنسيق مسؤولية العرض.
"""

from decimal import Decimal

from django.db.models import Avg, Count, Max, Min, Q, Sum

from apps.accounts.models import User
from apps.boxes.models import IntermediaryBox, ShopCashAccount, SmallOfficeAccount
from apps.core.models import JournalEntry
from apps.transactions.models import Transaction

ZERO = Decimal("0")


def _range_q(field, date_from, date_to):
    q = Q()
    if date_from:
        q &= Q(**{f"{field}__date__gte": date_from})
    if date_to:
        q &= Q(**{f"{field}__date__lte": date_to})
    return q


def _txns(tenant, date_from, date_to, *, created_by=None):
    qs = Transaction.objects.filter(_range_q("created_at", date_from, date_to))
    if created_by is not None:
        qs = qs.filter(created_by=created_by)
    return qs


def _accepted(tenant, date_from, date_to, *, created_by=None):
    return _txns(tenant, date_from, date_to, created_by=created_by).filter(
        approval_status=Transaction.Approval.ACCEPTED
    )


# ─────────────────────────────── 1. ملخص مالي لكل عملة
def summary_by_currency(tenant, date_from=None, date_to=None, user=None):
    links = SmallOfficeAccount.objects.select_related("account")
    if user is not None:
        links = links.filter(user=user)
    per = {}
    for link in links:
        bal = link.account.balance  # موجب = عليه
        row = per.setdefault(link.currency, [ZERO, ZERO])
        if bal > 0:
            row[0] += bal  # عليهم (لنا)
        elif bal < 0:
            row[1] += -bal  # لهم
    rows = [[c, str(owed), str(due), str(owed - due)] for c, (owed, due) in sorted(per.items())]
    return {
        "title": "الملخص المالي لكل عملة",
        "columns": ["العملة", "لنا (عليهم)", "لهم", "الصافي"],
        "rows": rows,
    }


# ─────────────────────────────── 2+9. الأرباح (فرق الأجور)
def profits(tenant, date_from=None, date_to=None, user=None):
    qs = _accepted(tenant, date_from, date_to, created_by=user)
    agg = (
        qs.values("currency_received")
        .annotate(
            count=Count("id"),
            fee_cost=Sum("fee_cost", default=0),
            fee_charged=Sum("fee_charged", default=0),
        )
        .order_by("currency_received")
    )
    rows = [
        [
            a["currency_received"],
            str(a["count"]),
            str(a["fee_charged"]),
            str(a["fee_cost"]),
            str(a["fee_charged"] - a["fee_cost"]),
        ]
        for a in agg
    ]
    return {
        "title": "الأرباح (فرق الأجور)",
        "columns": ["العملة", "عدد الحركات", "الأجور المستحقة", "رأس مال الأجور", "الربح"],
        "rows": rows,
    }


def profits_by_member(tenant, date_from=None, date_to=None, user=None):
    qs = _accepted(tenant, date_from, date_to)
    agg = (
        qs.values("created_by__first_name", "created_by__office_code", "currency_received")
        .annotate(
            count=Count("id"),
            fee_cost=Sum("fee_cost", default=0),
            fee_charged=Sum("fee_charged", default=0),
        )
        .order_by("created_by__office_code", "currency_received")
    )
    rows = [
        [
            f"{a['created_by__first_name']} ({a['created_by__office_code']})",
            a["currency_received"],
            str(a["count"]),
            str(a["fee_charged"] - a["fee_cost"]),
        ]
        for a in agg
    ]
    return {
        "title": "الأرباح حسب المكتب الصغير",
        "columns": ["المكتب", "العملة", "عدد الحركات", "الربح"],
        "rows": rows,
    }


# ─────────────────────────────── 3. حجم النشاط
def activity(tenant, date_from=None, date_to=None, user=None):
    qs = _accepted(tenant, date_from, date_to, created_by=user)
    agg = (
        qs.values("currency_received")
        .annotate(count=Count("id"), total=Sum("amount", default=0))
        .order_by("currency_received")
    )
    rows = [[a["currency_received"], str(a["count"]), str(a["total"])] for a in agg]
    return {
        "title": "حجم النشاط (الحركات المقبولة)",
        "columns": ["العملة", "عدد الحركات", "إجمالي المبالغ"],
        "rows": rows,
    }


# ─────────────────────────────── 4. ملخص المكاتب الصغيرة
def member_summary(tenant, date_from=None, date_to=None, user=None):
    members = User.objects.filter(role=User.Role.SMALL_OFFICE, tenant=tenant)
    rows = []
    for m in members:
        qs = _accepted(tenant, date_from, date_to, created_by=m)
        agg = qs.aggregate(
            count=Count("id"),
            total=Sum("amount", default=0),
            fees=Sum("fee_charged", default=0),
        )
        balances = "، ".join(
            f"{link.currency}: {link.account.balance}"
            for link in SmallOfficeAccount.objects.filter(user=m).select_related("account")
        )
        rows.append(
            [
                f"{m.first_name} ({m.office_code})",
                str(agg["count"]),
                str(agg["total"]),
                str(agg["fees"]),
                balances or "—",
            ]
        )
    return {
        "title": "ملخص المكاتب الصغيرة",
        "columns": [
            "المكتب",
            "عدد الحركات",
            "إجمالي المبالغ",
            "أجوره المستحقة",
            "أرصدته (موجب=عليه)",
        ],
        "rows": rows,
    }


# ─────────────────────────────── 5. ملخص الوسطاء
def box_summary(tenant, date_from=None, date_to=None, user=None):
    rows = []
    for box in IntermediaryBox.objects.prefetch_related("currency_accounts__account"):
        qs = _accepted(tenant, date_from, date_to).filter(box=box)
        agg = qs.values("currency_delivered").annotate(
            count=Count("id"), total=Sum("amount_delivered", default=0)
        )
        passed = {a["currency_delivered"]: a for a in agg}
        for link in box.currency_accounts.all():
            p = passed.get(link.currency, {"count": 0, "total": ZERO})
            rows.append(
                [
                    f"{box.name} #{box.number}",
                    link.currency,
                    str(p["count"]),
                    str(p["total"]),
                    str(link.account.balance),
                ]
            )
    return {
        "title": "ملخص صناديق الوسطاء",
        "columns": ["الصندوق", "العملة", "حركات مُرِّرت", "إجمالي المُمرَّر", "الرصيد الجاري"],
        "rows": rows,
    }


# ─────────────────────────────── 6. حركة صندوق المحل
def shop_cash_movement(tenant, date_from=None, date_to=None, user=None):
    rows = []
    for link in ShopCashAccount.objects.select_related("account"):
        qs = link.account.lines.filter(_range_q("created_at", date_from, date_to))
        agg = qs.aggregate(debit=Sum("debit", default=0), credit=Sum("credit", default=0))
        rows.append(
            [
                link.currency,
                str(agg["debit"]),
                str(agg["credit"]),
                str(agg["debit"] - agg["credit"]),
                str(link.account.balance),
            ]
        )
    return {
        "title": "حركة صندوق المحل (النقد)",
        "columns": ["العملة", "داخل", "خارج", "صافي الفترة", "الرصيد الجاري"],
        "rows": rows,
    }


# ─────────────────────────────── 7. حسب الحالة
def by_status(tenant, date_from=None, date_to=None, user=None):
    qs = _txns(tenant, date_from, date_to, created_by=user)
    rows = []
    for value, label in Transaction.Approval.choices:
        rows.append(["القبول", label, str(qs.filter(approval_status=value).count())])
    for value, label in Transaction.Payment.choices:
        rows.append(["الدفع", label, str(qs.filter(payment_status=value).count())])
    for value, label in Transaction.Delivery.choices:
        rows.append(["التسليم", label, str(qs.filter(delivery_status=value).count())])
    return {
        "title": "الحركات حسب الحالة",
        "columns": ["المحور", "الحالة", "العدد"],
        "rows": rows,
    }


# ─────────────────────────────── 8. حسب الوجهة
def by_destination(tenant, date_from=None, date_to=None, user=None):
    qs = _accepted(tenant, date_from, date_to, created_by=user)
    agg = (
        qs.values("destination", "currency_received")
        .annotate(count=Count("id"), total=Sum("amount", default=0))
        .order_by("-count")[:50]
    )
    rows = [
        [a["destination"], a["currency_received"], str(a["count"]), str(a["total"])] for a in agg
    ]
    return {
        "title": "الحركات حسب الوجهة",
        "columns": ["الوجهة", "العملة", "العدد", "الإجمالي"],
        "rows": rows,
    }


# ─────────────────────────────── 10. التسويات
def settlements(tenant, date_from=None, date_to=None, user=None):
    qs = JournalEntry.objects.filter(entry_type=JournalEntry.EntryType.SETTLEMENT).filter(
        _range_q("created_at", date_from, date_to)
    )
    if user is not None:
        member_accounts = SmallOfficeAccount.objects.filter(user=user).values_list(
            "account_id", flat=True
        )
        qs = qs.filter(lines__account_id__in=list(member_accounts)).distinct()
    rows = []
    for e in qs.order_by("-created_at")[:100]:
        total = e.lines.aggregate(d=Sum("debit", default=0))["d"]
        currency = e.lines.first().account.currency if e.lines.exists() else ""
        rows.append(
            [str(e.pk), e.memo, currency, str(total), e.created_at.strftime("%Y-%m-%d %H:%M")]
        )
    return {
        "title": "التسويات (اعتماد/سحب/قبض)",
        "columns": ["#", "البيان", "العملة", "المبلغ", "الوقت"],
        "rows": rows,
    }


# ─────────────────────────────── 11. أسعار الصرف
def exchange_rates(tenant, date_from=None, date_to=None, user=None):
    qs = _accepted(tenant, date_from, date_to, created_by=user).filter(exchange_rate__isnull=False)
    agg = (
        qs.values("currency_received", "currency_delivered")
        .annotate(
            count=Count("id"),
            avg=Avg("exchange_rate"),
            lo=Min("exchange_rate"),
            hi=Max("exchange_rate"),
        )
        .order_by("currency_received")
    )
    rows = [
        [
            f"{a['currency_received']} → {a['currency_delivered']}",
            str(a["count"]),
            str(round(a["avg"], 6)),
            str(a["lo"]),
            str(a["hi"]),
        ]
        for a in agg
    ]
    return {
        "title": "أسعار الصرف المستخدمة",
        "columns": ["الزوج", "العدد", "المتوسط", "الأدنى", "الأعلى"],
        "rows": rows,
    }


# ─────────────────────────────── 12. الأكثر نشاطاً
def top_members(tenant, date_from=None, date_to=None, user=None):
    qs = _accepted(tenant, date_from, date_to)
    agg = (
        qs.values("created_by__first_name", "created_by__office_code")
        .annotate(count=Count("id"), total=Sum("amount", default=0))
        .order_by("-count")[:10]
    )
    rows = [
        [
            str(i + 1),
            f"{a['created_by__first_name']} ({a['created_by__office_code']})",
            str(a["count"]),
            str(a["total"]),
        ]
        for i, a in enumerate(agg)
    ]
    return {
        "title": "أكثر المكاتب نشاطاً",
        "columns": ["#", "المكتب", "عدد الحركات", "إجمالي المبالغ"],
        "rows": rows,
    }


# ─────────────────────────────── 13. الكشف اليومي
def daily_close(tenant, date_from=None, date_to=None, user=None):
    # يُستخدم date_from كيوم الكشف (افتراضياً اليوم يُمرَّر من الواجهة)
    day = date_from or date_to
    act = activity(tenant, day, day, user)
    prof = profits(tenant, day, day, user)
    cash = shop_cash_movement(tenant, day, day, user)
    rows = (
        [["النشاط"] + r for r in act["rows"]]
        + [["الأرباح", r[0], r[4], ""] for r in prof["rows"]]
        + [["النقد", r[0], r[3], r[4]] for r in cash["rows"]]
    )
    return {
        "title": f"الكشف اليومي — {day or 'اليوم'}",
        "columns": ["المحور", "العملة", "قيمة 1", "قيمة 2"],
        "rows": rows,
    }


# سجل التقارير المركزي: النوع → (الدالة، متاح للصغير؟)
REPORTS = {
    "summary": (summary_by_currency, True),
    "profits": (profits, False),
    "profits_by_member": (profits_by_member, False),
    "activity": (activity, True),
    "member_summary": (member_summary, False),
    "box_summary": (box_summary, False),
    "shop_cash": (shop_cash_movement, False),
    "by_status": (by_status, True),
    "by_destination": (by_destination, True),
    "settlements": (settlements, True),
    "exchange_rates": (exchange_rates, True),
    "top_members": (top_members, False),
    "daily_close": (daily_close, False),
}

REPORT_LABELS = {
    "summary": "الملخص المالي لكل عملة",
    "profits": "الأرباح (فرق الأجور)",
    "profits_by_member": "الأرباح حسب المكتب",
    "activity": "حجم النشاط",
    "member_summary": "ملخص المكاتب الصغيرة",
    "box_summary": "ملخص الوسطاء",
    "shop_cash": "حركة صندوق المحل",
    "by_status": "الحركات حسب الحالة",
    "by_destination": "الحركات حسب الوجهة",
    "settlements": "التسويات",
    "exchange_rates": "أسعار الصرف",
    "top_members": "الأكثر نشاطاً",
    "daily_close": "الكشف اليومي",
}
