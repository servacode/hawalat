"""
حوالات — خدمات دورة الحركة (المرحلة 5)
==========================================
كل أفعال الحركة هنا حصراً: إنشاء/قبول/رفض/دفع/تسليم/تعديل.
القيود عبر محرك القيود فقط (post_entry/reverse_entry).

قيد القبول (الدورة §4-أ):
- عملة واحدة:  مدين الصغير (المبلغ+المستحقة) / دائن الصندوق (المبلغ+رأس المال)
               / دائن الربح (الفرق).
- عملتان: تُستخدم حسابات «مقاصة صرف» لكل عملة ليبقى القيد متوازناً لكل عملة:
    بالمقبوضة:  مدين الصغير (المبلغ+المستحقة) / دائن مقاصة (المبلغ+رأس المال)
                / دائن الربح (الفرق)
    بالمسلَّمة: مدين مقاصة (المبلغ المسلَّم) / دائن الصندوق (المبلغ المسلَّم)
  رصيد المقاصة يمثل مركز الصرف المفتوح — قابل للتدقيق.

قيد «مدفوعة» (§4-ب): مدين صندوق المحل / دائن الصغير (المبلغ+المستحقة) — يصفّي دينه.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.admin_panel.services import get_active_subscription
from apps.boxes.services import (
    check_credit_limit,
    get_box_account,
    get_fees_profit_account,
    get_shop_cash_account,
    get_small_office_account,
)
from apps.core.models import Account, JournalEntry, PlatformSettings
from apps.core.services import post_entry, reverse_entry

from .models import Transaction

ZERO = Decimal("0")


# ---------------------------------------------------------------- مساعدة


def _generate_reference(tenant) -> str:
    """رقم مرجعي فريد مرتبط بكود المكتب: HW-BIG001-000001 (المشهد 6)."""
    seq = Transaction.all_objects.filter(tenant=tenant).count() + 1
    while True:
        ref = f"HW-{tenant.code}-{seq:06d}"
        if not Transaction.all_objects.filter(reference_code=ref).exists():
            return ref
        seq += 1


def get_fx_clearing_account(tenant, currency: str) -> Account:
    account, _ = Account.all_objects.get_or_create(
        tenant=tenant,
        name="مقاصة الصرف",
        kind=Account.Kind.FX_CLEARING,
        currency=currency,
    )
    return account


def check_transactions_limit(tenant) -> tuple[bool, str]:
    """حد الحركات في الباقة (الجزء 18) مع قاعدة الترحيل (المشهد 1)."""
    if PlatformSettings.load().free_mode:
        return True, ""
    sub = get_active_subscription(tenant)
    if sub is None:
        return False, "لا يوجد اشتراك مفعّل — اطلب باقة من إدارة المنصة."
    counted = Transaction.all_objects.filter(
        tenant=tenant, created_at__gte=sub.activated_at
    ).count()
    if counted >= sub.package.max_transactions:
        return False, f"بلغت حد الباقة ({sub.package.max_transactions} حركة) — رقِّ الباقة."
    return True, ""


# ---------------------------------------------------------------- الإنشاء


@db_transaction.atomic
def create_transaction(
    *,
    tenant,
    created_by,
    sender: str,
    beneficiary: str,
    amount: Decimal,
    currency_received: str,
    currency_delivered: str,
    destination: str,
) -> Transaction:
    """إنشاء حركة (من الصغير، أو الكبير لنفسه) — تبدأ قيد الانتظار بلا قيود."""
    if amount <= ZERO:
        raise ValidationError("المبلغ يجب أن يكون موجباً.")
    ok, reason = check_transactions_limit(tenant)
    if not ok:
        raise ValidationError(reason)
    return Transaction.all_objects.create(
        tenant=tenant,
        created_by=created_by,
        reference_code=_generate_reference(tenant),
        sender=sender,
        beneficiary=beneficiary,
        amount=amount,
        currency_received=currency_received,
        currency_delivered=currency_delivered,
        destination=destination,
    )


# ---------------------------------------------------------------- القبول


def _approval_lines(txn: Transaction):
    """يبني أسطر قيد القبول (متوازنة لكل عملة)."""
    small_account = get_small_office_account(txn.created_by, txn.currency_received)
    profit = get_fees_profit_account(txn.tenant, txn.currency_received)
    box_account = get_box_account(txn.box, txn.currency_delivered)

    owed = txn.amount + txn.fee_charged  # على الصغير (بالمقبوضة)
    out_cost = txn.amount + txn.fee_cost  # كلفة التمرير (بالمقبوضة)
    margin = txn.fee_charged - txn.fee_cost  # الربح

    if not txn.is_dual_currency:
        return [
            (small_account, owed, ZERO),
            (box_account, ZERO, out_cost),
            (profit, ZERO, margin),
        ]

    fx_recv = get_fx_clearing_account(txn.tenant, txn.currency_received)
    fx_delv = get_fx_clearing_account(txn.tenant, txn.currency_delivered)
    return [
        # بالعملة المقبوضة
        (small_account, owed, ZERO),
        (fx_recv, ZERO, out_cost),
        (profit, ZERO, margin),
        # بالعملة المسلَّمة
        (fx_delv, txn.amount_delivered, ZERO),
        (box_account, ZERO, txn.amount_delivered),
    ]


@db_transaction.atomic
def approve_transaction(
    *,
    txn: Transaction,
    box,
    fee_cost: Decimal,
    fee_charged: Decimal,
    exchange_rate: Decimal | None = None,
    amount_delivered: Decimal | None = None,
) -> Transaction:
    """قبول الحركة (المشهد 2): لا قبول إلا باكتمال البيانات + فحص الحد."""
    if txn.approval_status != Transaction.Approval.PENDING:
        raise ValidationError("هذه الحركة ليست قيد الانتظار.")
    if fee_cost is None or fee_charged is None:
        raise ValidationError("أدخل رأس مال الأجور والأجور المستحقة قبل القبول.")
    if fee_cost < ZERO or fee_charged < ZERO:
        raise ValidationError("الأجور لا تكون سالبة.")

    txn.box = box
    txn.fee_cost = fee_cost
    txn.fee_charged = fee_charged

    if txn.is_dual_currency:
        if not exchange_rate or exchange_rate <= ZERO:
            raise ValidationError("سعر الصرف إلزامي قبل القبول عند اختلاف العملتين.")
        txn.exchange_rate = exchange_rate
        txn.amount_delivered = amount_delivered or (txn.amount * exchange_rate).quantize(
            Decimal("0.0001")
        )
    else:
        txn.exchange_rate = None
        txn.amount_delivered = txn.amount

    # فحص الحد السالب (الجزء 5): الدين الإضافي = المبلغ + المستحقة بالمقبوضة
    ok, reason = check_credit_limit(txn.created_by, txn.currency_received, txn.amount + fee_charged)
    if not ok:
        raise ValidationError(reason)

    entry = post_entry(
        tenant=txn.tenant,
        entry_type=JournalEntry.EntryType.TRANSACTION,
        memo=f"قبول {txn.reference_code}",
        lines=_approval_lines(txn),
    )
    txn.approval_entry = entry
    txn.approval_status = Transaction.Approval.ACCEPTED
    txn.approved_at = timezone.now()
    txn.save()
    return txn


def reject_transaction(txn: Transaction) -> Transaction:
    """رفض: ملغية بلا أي قيود (§4-د)."""
    if txn.approval_status != Transaction.Approval.PENDING:
        raise ValidationError("هذه الحركة ليست قيد الانتظار.")
    txn.approval_status = Transaction.Approval.CANCELLED
    txn.save(update_fields=["approval_status", "updated_at"])
    return txn


# ---------------------------------------------------------------- الدفع والتسليم


@db_transaction.atomic
def mark_paid(txn: Transaction) -> Transaction:
    """مدفوعة (§4-ب): نقد يدخل المحل بقيمة (المبلغ+المستحقة) ويُصفّى دين الصغير."""
    if txn.approval_status != Transaction.Approval.ACCEPTED:
        raise ValidationError("لا يمكن تعليم الدفع إلا لحركة مقبولة.")
    if txn.payment_status == Transaction.Payment.PAID:
        raise ValidationError("الحركة مدفوعة مسبقاً.")
    small_account = get_small_office_account(txn.created_by, txn.currency_received)
    shop = get_shop_cash_account(txn.tenant, txn.currency_received)
    amount = txn.amount + txn.fee_charged
    entry = post_entry(
        tenant=txn.tenant,
        entry_type=JournalEntry.EntryType.SETTLEMENT,
        memo=f"قبض نقدي {txn.reference_code}",
        lines=[(shop, amount, ZERO), (small_account, ZERO, amount)],
    )
    txn.payment_entry = entry
    txn.payment_status = Transaction.Payment.PAID
    txn.save(update_fields=["payment_entry", "payment_status", "updated_at"])
    return txn


def mark_delivered(txn: Transaction, delivered: bool = True) -> Transaction:
    """تم التسليم: متابعة فقط، بلا قيود (§4-ج) — قابلة للتجاوز."""
    txn.delivery_status = (
        Transaction.Delivery.DELIVERED if delivered else Transaction.Delivery.NOT_DELIVERED
    )
    txn.save(update_fields=["delivery_status", "updated_at"])
    return txn


# ---------------------------------------------------------------- التعديل والعكس


@db_transaction.atomic
def reverse_transaction(txn: Transaction, memo: str = "") -> Transaction:
    """عكس حركة مقبولة بالكامل (بديل الحذف §4-و): يعكس الدفع ثم القبول."""
    if txn.approval_status != Transaction.Approval.ACCEPTED:
        raise ValidationError("لا يُعكس إلا حركة مقبولة.")
    if txn.payment_entry_id:
        reverse_entry(txn.payment_entry, memo=f"عكس قبض {txn.reference_code}")
        txn.payment_status = Transaction.Payment.UNPAID
    reverse_entry(txn.approval_entry, memo=memo or f"عكس {txn.reference_code}")
    txn.approval_status = Transaction.Approval.REVERSED
    txn.save()
    return txn


@db_transaction.atomic
def edit_accepted_transaction(*, txn: Transaction, **new_values) -> Transaction:
    """
    تعديل حركة مقبولة (§4-هـ): عكس القيد الأصلي ثم إعادة الترحيل بالقيم الجديدة.
    ينعكس على الطرفين تلقائياً (نفس الحسابات).
    """
    if txn.approval_status != Transaction.Approval.ACCEPTED:
        raise ValidationError("التعديل المحاسبي متاح للحركات المقبولة فقط.")
    if txn.payment_entry_id:
        raise ValidationError("اعكس القبض أولاً قبل تعديل حركة مدفوعة.")

    reverse_entry(txn.approval_entry, memo=f"تعديل {txn.reference_code} — عكس الأصل")

    for field in (
        "sender",
        "beneficiary",
        "destination",
        "amount",
        "currency_received",
        "currency_delivered",
    ):
        if field in new_values and new_values[field] is not None:
            setattr(txn, field, new_values[field])

    box = new_values.get("box", txn.box)
    fee_cost = new_values.get("fee_cost", txn.fee_cost)
    fee_charged = new_values.get("fee_charged", txn.fee_charged)
    exchange_rate = new_values.get("exchange_rate", txn.exchange_rate)

    txn.approval_status = Transaction.Approval.PENDING
    txn.approval_entry = None
    txn.save()
    return approve_transaction(
        txn=txn,
        box=box,
        fee_cost=fee_cost,
        fee_charged=fee_charged,
        exchange_rate=exchange_rate,
    )
