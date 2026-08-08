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
from apps.core.format import fmt
from apps.core.models import AuditLog, JournalEntry
from apps.core.permissions import IsBigOffice, IsSmallOffice
from apps.notifications.models import Notification
from apps.notifications.services import notify, push_refresh

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
    get_small_office_account,
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

    @action(detail=True, methods=["get"])
    def movements(self, request, pk=None):
        """كل حركات الصندوق بعملة محددة مع فلاتر (ملاحظة 16): نوع/مكتب/تاريخ."""
        from apps.core.models import JournalLine

        from .models import BoxCurrencyAccount, SmallOfficeAccount

        box = self.get_object()
        currency = request.query_params.get("currency") or ""
        link = BoxCurrencyAccount.objects.filter(box=box, currency=currency).first()
        if link is None:
            return Response({"currency": currency, "balance": "0", "rows": [], "totals": {"in": "0", "out": "0"}})

        lines = (
            JournalLine.objects.filter(account=link.account)
            .select_related("entry")
            .order_by("-created_at")
        )
        if d := request.query_params.get("date_from"):
            lines = lines.filter(created_at__date__gte=d)
        if d := request.query_params.get("date_to"):
            lines = lines.filter(created_at__date__lte=d)

        # خريطة حساب المكتب الصغير → اسمه (لعرض صاحب العملية وفلترتها)
        member_map = {
            l.account_id: (l.user.first_name or l.user.username, l.user_id)
            for l in SmallOfficeAccount.objects.select_related("user").all()
        }
        if m := request.query_params.get("member"):
            member_account_ids = [aid for aid, (_, uid) in member_map.items() if str(uid) == m]
            entry_ids = JournalLine.objects.filter(account_id__in=member_account_ids).values_list(
                "entry_id", flat=True
            )
            lines = lines.filter(entry_id__in=list(entry_ids))

        lines = list(lines[:500])
        # أسطر القيود المقابلة (لتحديد صاحب العملية)
        siblings = JournalLine.objects.filter(entry_id__in=[l.entry_id for l in lines]).values(
            "entry_id", "account_id"
        )
        entry_members = {}
        for sib in siblings:
            info = member_map.get(sib["account_id"])
            if info:
                entry_members[sib["entry_id"]] = info[0]

        def classify(line):
            memo = line.entry.memo or ""
            et = line.entry.entry_type
            if et == JournalEntry.EntryType.TRANSACTION:
                return "transaction"
            if et == JournalEntry.EntryType.REVERSAL:
                return "reversal"
            if memo.startswith("اعتماد"):
                return "deposit"
            if memo.startswith("سحب"):
                return "withdraw"
            if memo.startswith("تسوية"):
                return "adjustment"
            return "settlement"

        rows = []
        for line in lines:
            rows.append(
                {
                    "id": line.pk,
                    "at": line.created_at,
                    "memo": line.entry.memo,
                    "kind": classify(line),
                    "member": entry_members.get(line.entry_id, ""),
                    "in": str(line.debit),
                    "out": str(line.credit),
                }
            )
        if k := request.query_params.get("kind"):
            rows = [r for r in rows if r["kind"] == k]

        total_in = sum(Decimal(r["in"]) for r in rows)
        total_out = sum(Decimal(r["out"]) for r in rows)
        return Response(
            {
                "currency": currency,
                "balance": str(link.account.balance),
                "totals": {"in": str(total_in), "out": str(total_out)},
                "rows": rows,
            }
        )

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        """تسوية رصيد الصندوق (إضافة/خصم) بسبب واضح إلزامي (ملاحظة 16)."""
        from .services import adjust_box

        box = self.get_object()
        try:
            entry = adjust_box(
                tenant=request.user.tenant,
                box=box,
                currency=request.data.get("currency", ""),
                amount=Decimal(str(request.data.get("amount", "0"))),
                direction=request.data.get("direction", ""),
                reason=request.data.get("reason", ""),
            )
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=400)
        except Exception:
            return Response({"detail": "بيانات التسوية غير صالحة."}, status=400)
        audit(
            request,
            "adjust_box",
            "journal_entry",
            entry.pk,
            box=box.name,
            direction=request.data.get("direction"),
            amount=str(request.data.get("amount")),
            currency=request.data.get("currency"),
        )
        return Response({"entry_id": entry.pk}, status=201)

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
        label = "اعتماد" if action_name == "deposit" else "سحب"
        notify(
            small_user,
            Notification.Type.SETTLEMENT,
            f"{label} {fmt(data['amount'])} {data['currency']} على حسابك",
            f"عبر صندوق {box.name}",
            entity="journal_entry",
            entity_id=entry.pk,
        )
        push_refresh(small_user, "balances")
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


class SmallCurrenciesView(APIView):
    """المكتب الصغير: قراءة عملات مستأجره (لاختيار العملة في الإرسال)."""

    permission_classes = [IsAuthenticated, IsSmallOffice]

    def get(self, request):
        return Response(CurrencySerializer(Currency.objects.filter(is_active=True), many=True).data)


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


class ReconciliationPdfView(APIView):
    """تنزيل سجل مطابقة مثبّت ملف PDF (ملاحظة 14) — الصغير لنفسه والكبير لعضوه."""

    permission_classes = [IsAuthenticated]

    def get(self, request, rec_id, user_id=None):
        from django.http import HttpResponse

        from apps.reports.export import to_pdf

        from .models import Reconciliation

        if user_id is None:
            if request.user.role != User.Role.SMALL_OFFICE:
                return Response(status=status.HTTP_403_FORBIDDEN)
            target = request.user
        else:
            if request.user.role != User.Role.BIG_OFFICE:
                return Response(status=status.HTTP_403_FORBIDDEN)
            target = User.objects.filter(
                pk=user_id, tenant=request.user.tenant, role=User.Role.SMALL_OFFICE
            ).first()
            if target is None:
                return Response(status=status.HTTP_403_FORBIDDEN)

        rec = Reconciliation.all_objects.filter(user=target, pk=rec_id).first()
        if rec is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        name = target.first_name or target.username
        report = {
            "title": f"مطابقة {name} ({target.office_code}) — {rec.created_at:%Y-%m-%d %H:%M}",
            "columns": ["العملة", "الرصيد السابق", "عليه (الفترة)", "له (الفترة)", "الصافي المثبّت"],
            "rows": [
                [
                    r.get("currency", ""),
                    fmt(r["previous"]) if "previous" in r else "—",
                    fmt(r["debits"]) if "debits" in r else "—",
                    fmt(r["credits"]) if "credits" in r else "—",
                    fmt(r.get("balance", 0)),
                ]
                for r in rec.snapshot
            ],
        }
        resp = HttpResponse(to_pdf(report), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="reconciliation-{rec.pk}.pdf"'
        return resp


class ReconciliationHistoryView(APIView):
    """سجل المطابقات المثبّتة (ملاحظة التجربة 12): مرجع دائم يُعاد إليه عند أي خلاف."""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        from .models import Reconciliation

        # نفس منطق الهدف في ReconciliationView: الصغير نفسه أو عضو عند الكبير
        if user_id is None:
            if request.user.role != User.Role.SMALL_OFFICE:
                return Response(status=status.HTTP_403_FORBIDDEN)
            target = request.user
        else:
            if request.user.role != User.Role.BIG_OFFICE:
                return Response(status=status.HTTP_403_FORBIDDEN)
            target = User.objects.filter(
                pk=user_id, tenant=request.user.tenant, role=User.Role.SMALL_OFFICE
            ).first()
            if target is None:
                return Response(status=status.HTTP_403_FORBIDDEN)

        recs = Reconciliation.all_objects.filter(user=target).order_by("-created_at")[:200]
        return Response(
            [
                {
                    "id": r.pk,
                    "at": r.created_at,
                    "by": (r.created_by.first_name or r.created_by.username)
                    if r.created_by
                    else "—",
                    "by_role": r.created_by.role if r.created_by else "",
                    "rows": r.snapshot,
                }
                for r in recs
            ]
        )


class ReconciliationView(APIView):
    """مطابقة مكتب صغير (المشهد 4) — GET معاينة، POST تثبيت (نقطة إغلاق جديدة)."""

    permission_classes = [IsAuthenticated]

    def _target(self, request, user_id):
        from .services import build_reconciliation  # noqa: F401

        if user_id is None:
            # الصغير يطابق نفسه
            if request.user.role != User.Role.SMALL_OFFICE:
                return None
            return request.user
        # الكبير يطابق أحد أعضائه
        if request.user.role != User.Role.BIG_OFFICE:
            return None
        return User.objects.filter(
            pk=user_id, tenant=request.user.tenant, role=User.Role.SMALL_OFFICE
        ).first()

    def get(self, request, user_id=None):
        from .services import build_reconciliation

        target = self._target(request, user_id)
        if target is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        data = build_reconciliation(target)
        return Response(
            {
                "user": target.first_name or target.username,
                "office_code": target.office_code,
                "last_at": data["last_at"],
                "rows": data["rows"],
                # التثبيت للكبير حصراً (ملاحظة 14) — الصغير مشاهدة وتنزيل فقط
                "allowed": request.user.role == User.Role.BIG_OFFICE,
            }
        )

    def post(self, request, user_id=None):
        from .services import commit_reconciliation

        target = self._target(request, user_id)
        if target is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        # التثبيت من المكتب الكبير حصراً (ملاحظة 14) — الصغير يشاهد وينزّل فقط
        if request.user.role == User.Role.SMALL_OFFICE:
            return Response(
                {"detail": "المطابقة تُثبّت من مكتبك فقط — يمكنك مشاهدتها وتنزيلها PDF."},
                status=status.HTTP_403_FORBIDDEN,
            )
        rec, data = commit_reconciliation(target, created_by=request.user)
        AuditLog.objects.create(
            tenant=target.tenant,
            actor=request.user,
            action="commit_reconciliation",
            entity="reconciliation",
            entity_id=str(rec.pk),
        )
        # إشعار الطرف الآخر بالمطابقة (الجزء 20-أ)
        other = (
            target
            if request.user.id != target.id
            else User.objects.filter(tenant=target.tenant, role=User.Role.BIG_OFFICE).first()
        )
        if other is not None and other.id != request.user.id:
            notify(
                other,
                Notification.Type.RECONCILIATION,
                f"مطابقة جديدة — {target.first_name or target.username}",
                "ثُبّتت نقطة إغلاق جديدة.",
                entity="reconciliation",
                entity_id=rec.pk,
            )
        return Response(
            {
                "id": rec.pk,
                "user": target.first_name or target.username,
                "office_code": target.office_code,
                "at": rec.created_at,
                "last_at": data["last_at"],
                "rows": data["rows"],
            },
            status=status.HTTP_201_CREATED,
        )


class SmallStatementView(APIView):
    """كشف حساب المكتب الصغير لنفسه بعملة محددة."""

    permission_classes = [IsAuthenticated, IsSmallOffice]

    def get(self, request):
        currency = request.query_params.get("currency")
        if not currency:
            return Response({"detail": "حدد العملة."}, status=400)
        account = get_small_office_account(request.user, currency)
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


class MemberStatementView(APIView):
    """كشف حساب عضو (مكتب صغير) بعملة محددة — للكبير."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request, user_id):
        member = User.objects.filter(
            pk=user_id, tenant=request.user.tenant, role=User.Role.SMALL_OFFICE
        ).first()
        if member is None:
            return Response(status=404)
        currency = request.query_params.get("currency")
        if not currency:
            return Response({"detail": "حدد العملة."}, status=400)
        account = get_small_office_account(member, currency)
        data = account_statement(account)
        return Response(
            {
                "member": member.first_name or member.username,
                "currency": currency,
                "balance": str(data["balance"]),
                "lines": [
                    {**line, "debit": str(line["debit"]), "credit": str(line["credit"])}
                    for line in data["lines"]
                ],
            }
        )
