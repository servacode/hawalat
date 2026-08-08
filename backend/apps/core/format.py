"""
حوالات — تنسيق المبالغ المركزي للنصوص المولّدة من الخادم (ملاحظة 16)
========================================================================
كل مبلغ يظهر في نص (إشعار/واتساب/تصدير) يمرّ من هنا — بلا أصفار زائدة.
"""

from decimal import Decimal


def fmt(value) -> str:
    """1000.0000 → 1,000 · 10.5000 → 10.5 · يقبل Decimal/str/None."""
    if value is None:
        return "—"
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    d = d.normalize()
    # normalize قد يعطي صيغة أسية للأصفار الكبيرة (1E+3) — نعيدها عادية
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{d:,f}"
