"""
حوالات — نقاط الصناديق والعملات والتسويات
=============================================
كل شيء معزول بالمستأجر تلقائياً (TenantMiddleware + TenantManager).
- المكتب الكبير: إدارة كاملة (عملات، صناديق، حدود، اعتماد/سحب، عكس قيد، كشوف).
- المكتب الصغير: قراءة أرصدته فقط (صناديقه لكل عملة).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.models import AuditLog, JournalEntry
from apps.core.permissions import IsBigOffice, IsSmallOffice

from .models import CreditLimit, Currency, IntermediaryBox, SmallOfficeAccount
from .serializers import (
    CreditLimitSerializer,
    CurrencySerializer,
    IntermediaryBoxSerializer,
    SettlementSerializer,
)
from .services import (
    account_statement,
    deposit_to_box,
    get_box_account,
    get_shop_cash_account,
    reverse_entry,
    withdraw_from_box,
)


def audit(request, action_name, entity, entity_id, **data):
    AuditLog.objects.create(
        tenant=request.user.tenant,
        actor=request.user,
        action=action_name,
        entity=entity,
        entity_id=str(entity_id),
        data=data,
    )


class CurrencyViewSet(viewsets.ModelViewSet):
    """عملات المستأجر — يديرها المكتب الكبير (الجزء 17)."""

    permission_classes = [IsAuthenticated, IsBigOffice]
    serializer_class = CurrencySerializer
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        return Currency.objects.all()

    def perform_create(self, serializer):
        obj = serializer.save(tenant=self.request.user.tenant)
        audit(self.request, "create_currency", "currency", obj.pk, code=obj.code)


class IntermediaryBoxViewSet(viewsets.ModelViewSet):
    """صناديق الوسطاء: إضافة/تعديل + أرصدة + كشف + اعتماد/سحب (الأجزاء 12، المشهد 5)."""

    permission_classes = [IsAuthenticated, IsBigOffice]
    serializer_class = IntermediaryBoxSerializer
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        return IntermediaryBox.objects.prefetch_related("currencies", "currency_accounts__account")

    def perform_create(self, serializer):
        obj = serializer.save(tenant=self.request.user.tenant)
        audit(self.request, "create_box", "intermediary_box", obj.pk, name=obj.name)

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        """كشف الصندوق بعملة محددة: ?currency=USD"""
        box = self.get_object()
        currency = request.query_params.get("currency")
        if not currency:
            return Response(
                {"detail": "حدد العملة: ?currency=USD"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            account = get_box_account(box, currency)
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        data = account_statement(account)
        return Response(
            {
                "box": box.name,
                "currency": currency,
                "balance": str(data["balance"]),
                "lines": [
                    {**line, "debit": str(line["debit"]), "credit": str(line["credit"])}
                    for line in data["lines"]
                ],
            }
        )

    @action(detail=True, methods=["post"])
    def deposit(self, request, pk=None):
        """اعتماد باسم مكتب صغير (المشهد 5)."""
        return self._settle(request, pk, deposit_to_box, "deposit")

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        """سحب باسم مكتب صغير (عكس الاعتماد)."""
        return self._settle(request, pk, withdraw_from_box, "withdraw")

    def _settle(self, request, pk, fn, action_name):
        box = self.get_object()
        serializer = SettlementSerializer(data={**request.data, "box": pk})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        small_user = User.objects.filter(
            pk=data["small_user"],
            tenant=request.user.tenant,
            role=User.Role.SMALL_OFFICE,
        ).first()
        if small_user is None:
            return Response({"detail": "المكتب الصغير غير موجود ضمن مكتبك."}, status=400)
        try:
            entry = fn(
                tenant=request.user.tenant,
                box=box,
                small_user=small_user,
                currency=data["currency"],
                amount=Decimal(data["amount"]),
                memo=data["memo"],
            )
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        audit(
            request,
            action_name,
            "journal_entry",
            entry.pk,
            box=box.name,
            amount=str(data["amount"]),
            currency=data["currency"],
        )
        return Response({"entry_id": entry.pk}, status=status.HTTP_201_CREATED)


class CreditLimitViewSet(viewsets.ModelViewSet):
    """الحدود السالبة لكل (مكتب صغير × عملة) — يضبطها الكبير (الجزء 5)."""

    permission_classes = [IsAuthenticated, IsBigOffice]
    serializer_class = CreditLimitSerializer
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        return CreditLimit.objects.select_related("user")

    def perform_create(self, serializer):
        user = serializer.validated_data["user"]
        if user.tenant_id != self.request.user.tenant_id:
            raise ValidationError("المكتب الصغير ليس ضمن مكتبك.")
        obj = serializer.save(tenant=self.request.user.tenant)
        audit(
            self.request,
            "set_credit_limit",
            "credit_limit",
            obj.pk,
            user=user.username,
            currency=obj.currency,
            limit=str(obj.negative_limit),
        )


class ReverseEntryView(APIView):
    """عكس قيد — بديل الحذف الوحيد (ق3)."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def post(self, request, entry_id):
        entry = JournalEntry.objects.filter(pk=entry_id).first()
        if entry is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            mirror = reverse_entry(entry, memo=request.data.get("memo", ""))
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        audit(request, "reverse_entry", "journal_entry", entry.pk, mirror=mirror.pk)
        return Response({"reversal_entry_id": mirror.pk}, status=201)


class ShopCashView(APIView):
    """صندوق المحل: أرصدة النقد لكل عملة + كشف."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request):
        currency = request.query_params.get("currency")
        if currency:
            account = get_shop_cash_account(request.user.tenant, currency)
            data = account_statement(account)
            return Response(
                {
                    "currency": currency,
                    "balance": str(data["balance"]),
                    "lines": [
                        {**line, "debit": str(line["debit"]), "credit": str(line["credit"])}
                        for line in data["lines"]
                    ],
                }
            )
        balances = [
            {
                "currency": c.code,
                "balance": str(get_shop_cash_account(request.user.tenant, c.code).balance),
            }
            for c in Currency.objects.filter(is_active=True)
        ]
        return Response({"balances": balances})


class MyBalancesView(APIView):
    """المكتب الصغير: صناديقه لكل عملة (له/عليه/الصافي) — الجزء 3-د."""

    permission_classes = [IsAuthenticated, IsSmallOffice]

    def get(self, request):
        links = SmallOfficeAccount.objects.filter(user=request.user).select_related("account")
        balances = []
        for link in links:
            bal = link.account.balance  # موجب = عليه للكبير
            balances.append(
                {
                    "currency": link.currency,
                    "owed_by_me": str(bal) if bal > 0 else "0",  # عليه
                    "owed_to_me": str(-bal) if bal < 0 else "0",  # له
                    "net": str(-bal),  # من منظور الصغير: موجب = له
                }
            )
        return Response({"balances": balances})
