"""
حوالات — نقاط الحركات (المرحلة 5)
====================================
- الصغير: إنشاء + سجل حركاته (فلاتر).
- الكبير: الجارية (قيد الانتظار) + معالجة (قبول/رفض) + سجل (فلاتر)
  + مدفوعة/تسليم + عكس/تعديل. حركة الكبير لنفسه من نفس النقاط (المشهد 3).
"""

from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.boxes.models import IntermediaryBox
from apps.core.models import AuditLog
from apps.core.permissions import IsBigOffice
from apps.notifications.models import Notification
from apps.notifications.services import notify, push_refresh

from .models import Transaction
from .serializers import (
    ApproveSerializer,
    CreateTransactionSerializer,
    TransactionSerializer,
)
from .services import (
    approve_transaction,
    create_transaction,
    mark_delivered,
    mark_paid,
    reject_transaction,
    reverse_transaction,
)


def audit(request, action_name, txn, **data):
    AuditLog.objects.create(
        tenant=request.user.tenant,
        actor=request.user,
        action=action_name,
        entity="transaction",
        entity_id=txn.reference_code,
        data=data,
    )


def apply_filters(qs, params):
    """فلتر موحّد للسجلات (الجزء 11): حالة/عملة/بحث/تاريخ/منشئ."""
    if s := params.get("approval"):
        qs = qs.filter(approval_status=s)
    if s := params.get("payment"):
        qs = qs.filter(payment_status=s)
    if s := params.get("delivery"):
        qs = qs.filter(delivery_status=s)
    if c := params.get("currency"):
        qs = qs.filter(currency_received=c)
    if u := params.get("created_by"):
        qs = qs.filter(created_by_id=u)
    if d := params.get("date_from"):
        qs = qs.filter(created_at__date__gte=d)
    if d := params.get("date_to"):
        qs = qs.filter(created_at__date__lte=d)
    if q := params.get("q"):
        from django.db.models import Q

        qs = qs.filter(
            Q(reference_code__icontains=q)
            | Q(sender__icontains=q)
            | Q(beneficiary__icontains=q)
            | Q(destination__icontains=q)
        )
    return qs


class MyTransactionsViewSet(viewsets.ViewSet):
    """المكتب الصغير: إنشاء حركة + سجل حركاته. (الكبير أيضاً يُنشئ لنفسه من هنا.)"""

    permission_classes = [IsAuthenticated]

    def _own_qs(self, request):
        return Transaction.objects.filter(created_by=request.user).select_related(
            "box", "created_by"
        )

    def list(self, request):
        qs = apply_filters(self._own_qs(request), request.query_params)
        page = qs[:200]
        return Response(TransactionSerializer(page, many=True).data)

    def create(self, request):
        if request.user.role not in (User.Role.SMALL_OFFICE, User.Role.BIG_OFFICE):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = CreateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            txn = create_transaction(
                tenant=request.user.tenant,
                created_by=request.user,
                **serializer.validated_data,
            )
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        audit(request, "create_transaction", txn)
        # إشعار الكبير بوصول حركة جديدة + تحديث لحظي لقائمة الجارية (الجزء 20-أ)
        big = User.objects.filter(tenant=request.user.tenant, role=User.Role.BIG_OFFICE).first()
        if big and big.id != request.user.id:
            notify(
                big,
                Notification.Type.TXN_NEW,
                f"حركة جديدة {txn.reference_code}",
                f"من {request.user.first_name or request.user.username}: {txn.amount} {txn.currency_received} → {txn.destination}",
                entity="transaction",
                entity_id=txn.id,
            )
        if big:
            push_refresh(big, "pending")
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class OfficeTransactionsViewSet(viewsets.ViewSet):
    """المكتب الكبير: الجارية + السجل + كل أفعال المعالجة."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def _qs(self):
        return Transaction.objects.select_related("box", "created_by")

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """الحركات الجارية = قيد الانتظار فقط (الجزء 11)."""
        qs = apply_filters(
            self._qs().filter(approval_status=Transaction.Approval.PENDING),
            request.query_params,
        )
        return Response(TransactionSerializer(qs[:200], many=True).data)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """السجل = كل ما نُفّذ (مقبولة/ملغية/معكوسة) مع فلتر احترافي."""
        qs = apply_filters(
            self._qs().exclude(approval_status=Transaction.Approval.PENDING),
            request.query_params,
        )
        return Response(TransactionSerializer(qs[:200], many=True).data)

    def retrieve(self, request, pk=None):
        txn = self._qs().filter(pk=pk).first()
        if txn is None:
            return Response(status=404)
        return Response(TransactionSerializer(txn).data)

    def _get(self, pk):
        return Transaction.objects.filter(pk=pk).first()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        txn = self._get(pk)
        if txn is None:
            return Response(status=404)
        serializer = ApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        box = IntermediaryBox.objects.filter(pk=data["box"], is_active=True).first()
        if box is None:
            return Response({"detail": "صندوق الوسيط غير موجود."}, status=400)
        try:
            approve_transaction(
                txn=txn,
                box=box,
                fee_cost=data["fee_cost"],
                fee_charged=data["fee_charged"],
                exchange_rate=data.get("exchange_rate"),
                amount_delivered=data.get("amount_delivered"),
            )
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        audit(request, "approve_transaction", txn, box=box.name)
        if txn.created_by_id != request.user.id:
            notify(
                txn.created_by,
                Notification.Type.TXN_ACCEPTED,
                f"قُبلت حركتك {txn.reference_code}",
                f"الأجور المستحقة: {txn.fee_charged} {txn.currency_received}",
                entity="transaction",
                entity_id=txn.id,
            )
            push_refresh(txn.created_by, "balances")
        return Response(TransactionSerializer(txn).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        txn = self._get(pk)
        if txn is None:
            return Response(status=404)
        try:
            reject_transaction(txn)
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        audit(request, "reject_transaction", txn)
        if txn.created_by_id != request.user.id:
            notify(
                txn.created_by,
                Notification.Type.TXN_REJECTED,
                f"رُفضت حركتك {txn.reference_code}",
                "",
                entity="transaction",
                entity_id=txn.id,
            )
        return Response(TransactionSerializer(txn).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        txn = self._get(pk)
        if txn is None:
            return Response(status=404)
        try:
            mark_paid(txn)
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        audit(request, "mark_paid", txn)
        if txn.created_by_id != request.user.id:
            notify(
                txn.created_by,
                Notification.Type.TXN_PAID,
                f"قُبضت حركتك {txn.reference_code} نقداً",
                f"{txn.amount + txn.fee_charged} {txn.currency_received} — صُفّي حسابها",
                entity="transaction",
                entity_id=txn.id,
            )
            push_refresh(txn.created_by, "balances")
        return Response(TransactionSerializer(txn).data)

    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        txn = self._get(pk)
        if txn is None:
            return Response(status=404)
        mark_delivered(txn, request.data.get("delivered", True))
        audit(request, "mark_delivered", txn)
        return Response(TransactionSerializer(txn).data)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        txn = self._get(pk)
        if txn is None:
            return Response(status=404)
        try:
            reverse_transaction(txn, memo=request.data.get("memo", ""))
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        audit(request, "reverse_transaction", txn)
        if txn.created_by_id != request.user.id:
            notify(
                txn.created_by,
                Notification.Type.TXN_REVERSED,
                f"عُكست/عُدّلت حركتك {txn.reference_code}",
                "",
                entity="transaction",
                entity_id=txn.id,
            )
            push_refresh(txn.created_by, "balances")
        return Response(TransactionSerializer(txn).data)
