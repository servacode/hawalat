"""
حوالات — اختبارات الحركات (المرحلة 5)
=========================================
تفحص المشهد 2 بالكامل عبر API، ثنائية العملة (مقاصة متوازنة)، الحد السالب
عند القبول، مدفوعة/تسليم، عكس/تعديل، حد الباقة، وقواعد الصلاحيات.
"""

from decimal import Decimal

from django.urls import reverse as url
from rest_framework.test import APITestCase

from apps.accounts.services import create_big_office, create_small_office
from apps.boxes.models import Currency, IntermediaryBox
from apps.boxes.services import (
    deposit_to_box,
    get_box_account,
    get_shop_cash_account,
    get_small_office_account,
)
from apps.core.tenancy import tenant_context

from .models import Transaction
from .services import get_fx_clearing_account

D = Decimal
PASSWORD = "secret12345"


class BaseTxnTestCase(APITestCase):
    def setUp(self):
        self.big = create_big_office(name="مكتب دمشق", username="damascus", password=PASSWORD)
        self.tenant = self.big.tenant
        self.small = create_small_office(
            tenant=self.tenant, name="مكتب حلب", username="aleppo", password=PASSWORD
        )
        with tenant_context(self.tenant):
            self.try_ = Currency.objects.get(code="TRY")
            self.syp = Currency.objects.get(code="SYP")
            self.usd = Currency.objects.get(code="USD")
            self.box = IntermediaryBox.objects.create(name="الوعد", number="101")
            self.box.currencies.add(self.try_, self.syp, self.usd)
        # حد سالب واسع افتراضياً
        self.auth("damascus")
        for c in ("TRY", "SYP", "USD"):
            self.client.post(
                "/api/office/credit-limits/",
                {"user": self.small.pk, "currency": c, "negative_limit": "1000000"},
                format="json",
            )

    def auth(self, username):
        res = self.client.post(
            url("auth-login"), {"username": username, "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res

    def send_txn(self, **over):
        payload = {
            "sender": "أحمد سالم",
            "beneficiary": "مروان حدّاد",
            "amount": "1000",
            "currency_received": "USD",
            "currency_delivered": "USD",
            "destination": "دمشق",
            **over,
        }
        return self.client.post("/api/my/transactions/", payload, format="json")


class CreateFlowTests(BaseTxnTestCase):
    def test_sender_is_optional_but_rest_required(self):
        """اسم المرسِل اختياري — وبقية الحقول إجبارية."""
        self.auth("aleppo")
        payload = {
            "beneficiary": "مروان حدّاد",
            "amount": "500",
            "currency_received": "USD",
            "currency_delivered": "USD",
            "destination": "دمشق",
        }
        res = self.client.post("/api/my/transactions/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["sender"], "")

        for missing in ("beneficiary", "amount", "currency_received", "destination"):
            bad = {k: v for k, v in payload.items() if k != missing}
            res = self.client.post("/api/my/transactions/", bad, format="json")
            self.assertEqual(res.status_code, 400, f"الحقل {missing} يجب أن يكون إجبارياً")

    def test_small_creates_pending_with_reference(self):
        self.auth("aleppo")
        res = self.send_txn()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["approval_status"], "pending")
        self.assertRegex(res.data["reference_code"], r"^HW-\d{6}$")

    def test_unknown_currency_rejected(self):
        self.auth("aleppo")
        res = self.send_txn(currency_received="XXX")
        self.assertEqual(res.status_code, 400)

    def test_big_office_self_transaction_same_flow(self):
        """المشهد 3: الكبير يرسل لنفسه من نفس النقاط."""
        self.auth("damascus")
        res = self.send_txn()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["created_by_code"], "BIG001")


class ApproveSingleCurrencyTests(BaseTxnTestCase):
    """المشهد 2 الحرفي: 1000 / رأس مال 10 / مستحقة 15 → قيود متوازنة."""

    def _approve(self, txn_id, **over):
        payload = {"box": self.box.pk, "fee_cost": "10", "fee_charged": "15", **over}
        return self.client.post(
            f"/api/office/transactions/{txn_id}/approve/", payload, format="json"
        )

    def test_scene2_balances(self):
        # إيداع تمهيدي 2000 في الوعد (ليطابق سرد 990)
        deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("2000"),
        )
        self.auth("aleppo")
        txn_id = self.send_txn().data["id"]

        self.auth("damascus")
        res = self._approve(txn_id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["approval_status"], "accepted")

        with tenant_context(self.tenant):
            small_acc = get_small_office_account(self.small, "USD")
            box_acc = get_box_account(self.box, "USD")
            # الصغير: −2000 (له) + 1015 (عليه) = −985
            self.assertEqual(small_acc.balance, D("-985"))
            # الصندوق: 2000 − 1010 = 990 (السرد الحرفي)
            self.assertEqual(box_acc.balance, D("990"))

    def test_approve_requires_fees(self):
        self.auth("aleppo")
        txn_id = self.send_txn().data["id"]
        self.auth("damascus")
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/approve/",
            {"box": self.box.pk},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_reject_no_entries(self):
        self.auth("aleppo")
        txn_id = self.send_txn().data["id"]
        self.auth("damascus")
        res = self.client.post(f"/api/office/transactions/{txn_id}/reject/")
        self.assertEqual(res.data["approval_status"], "cancelled")
        with tenant_context(self.tenant):
            self.assertEqual(get_small_office_account(self.small, "USD").balance, D("0"))


class DualCurrencyTests(BaseTxnTestCase):
    """الجزء 8: قبض TRY وتسليم SYP بسعر صرف مثبّت — متوازن لكل عملة."""

    def test_rate_required(self):
        self.auth("aleppo")
        txn_id = self.send_txn(
            currency_received="TRY", currency_delivered="SYP", amount="7500"
        ).data["id"]
        self.auth("damascus")
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/approve/",
            {"box": self.box.pk, "fee_cost": "100", "fee_charged": "150"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("سعر الصرف", res.data["detail"])

    def test_dual_currency_balances(self):
        self.auth("aleppo")
        txn_id = self.send_txn(
            currency_received="TRY", currency_delivered="SYP", amount="1000"
        ).data["id"]

        self.auth("damascus")
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/approve/",
            {
                "box": self.box.pk,
                "fee_cost": "10",
                "fee_charged": "15",
                "exchange_rate": "400",  # 1 TRY = 400 SYP
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(D(res.data["amount_delivered"]), D("400000"))

        with tenant_context(self.tenant):
            small_try = get_small_office_account(self.small, "TRY")
            box_syp = get_box_account(self.box, "SYP")
            fx_try = get_fx_clearing_account(self.tenant, "TRY")
            fx_syp = get_fx_clearing_account(self.tenant, "SYP")
            self.assertEqual(small_try.balance, D("1015"))  # عليه بالتركي
            self.assertEqual(box_syp.balance, D("-400000"))  # الصندوق نقص بالسوري
            self.assertEqual(fx_try.balance, D("-1010"))  # مركز الصرف تركي
            self.assertEqual(fx_syp.balance, D("400000"))  # مركز الصرف سوري
            # توازن كل عملة: TRY: 1015−1010−5=0 ✓، SYP: 400000−400000=0 ✓


class CreditLimitOnApproveTests(BaseTxnTestCase):
    def test_limit_blocks_approval(self):
        """الجزء 5: تجاوز الحد يمنع القبول برسالة تعزيز الرصيد."""
        self.auth("damascus")
        self.client.patch  # noqa
        # حد ضيّق 500 دولار
        from apps.boxes.models import CreditLimit

        with tenant_context(self.tenant):
            CreditLimit.objects.filter(user=self.small, currency="USD").update(
                negative_limit=D("500")
            )
        self.auth("aleppo")
        txn_id = self.send_txn(amount="1000").data["id"]
        self.auth("damascus")
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/approve/",
            {"box": self.box.pk, "fee_cost": "10", "fee_charged": "15"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("تعزيز", res.data["detail"])
        # الحركة تبقى قيد الانتظار
        txn = Transaction.all_objects.get(pk=txn_id)
        self.assertEqual(txn.approval_status, "pending")


class PaymentDeliveryTests(BaseTxnTestCase):
    def _accepted(self):
        self.auth("aleppo")
        txn_id = self.send_txn().data["id"]
        self.auth("damascus")
        self.client.post(
            f"/api/office/transactions/{txn_id}/approve/",
            {"box": self.box.pk, "fee_cost": "10", "fee_charged": "15"},
            format="json",
        )
        return txn_id

    def test_paid_moves_cash_and_clears_debt(self):
        """§4-ب: مدفوعة = المبلغ+المستحقة نقداً، ويُصفّى دين الصغير."""
        txn_id = self._accepted()
        res = self.client.post(f"/api/office/transactions/{txn_id}/pay/")
        self.assertEqual(res.data["payment_status"], "paid")
        with tenant_context(self.tenant):
            self.assertEqual(get_shop_cash_account(self.tenant, "USD").balance, D("1015"))
            self.assertEqual(get_small_office_account(self.small, "USD").balance, D("0"))

    def test_cannot_pay_twice(self):
        txn_id = self._accepted()
        self.client.post(f"/api/office/transactions/{txn_id}/pay/")
        res = self.client.post(f"/api/office/transactions/{txn_id}/pay/")
        self.assertEqual(res.status_code, 400)

    def test_delivered_is_status_only(self):
        txn_id = self._accepted()
        res = self.client.post(f"/api/office/transactions/{txn_id}/deliver/")
        self.assertEqual(res.data["delivery_status"], "delivered")

    def test_delivered_notifies_small_office(self):
        """ملاحظة التجربة 7: الصغير يعرف أن حركة زبونه سُلّمت."""
        from apps.notifications.models import Notification

        txn_id = self._accepted()
        self.client.post(f"/api/office/transactions/{txn_id}/deliver/")
        notif = Notification.objects.filter(
            recipient=self.small, ntype=Notification.Type.TXN_DELIVERED
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("سُلّمت حركتك", notif.title)


class ReverseEditTests(BaseTxnTestCase):
    def _accepted(self):
        self.auth("aleppo")
        txn_id = self.send_txn().data["id"]
        self.auth("damascus")
        self.client.post(
            f"/api/office/transactions/{txn_id}/approve/",
            {"box": self.box.pk, "fee_cost": "10", "fee_charged": "15"},
            format="json",
        )
        return txn_id

    def test_reverse_restores_all(self):
        txn_id = self._accepted()
        self.client.post(f"/api/office/transactions/{txn_id}/pay/")
        res = self.client.post(f"/api/office/transactions/{txn_id}/reverse/")
        self.assertEqual(res.data["approval_status"], "reversed")
        with tenant_context(self.tenant):
            self.assertEqual(get_small_office_account(self.small, "USD").balance, D("0"))
            self.assertEqual(get_box_account(self.box, "USD").balance, D("0"))
            self.assertEqual(get_shop_cash_account(self.tenant, "USD").balance, D("0"))


class NoReverseAfterDeliveryTests(ReverseEditTests):
    """ملاحظة التجربة 7: بعد التسليم لا عكس ولا تعديل — الزبون استلم المال فعلياً."""

    def test_reverse_blocked_after_delivery(self):
        txn_id = self._accepted()
        self.client.post(f"/api/office/transactions/{txn_id}/deliver/")
        res = self.client.post(f"/api/office/transactions/{txn_id}/reverse/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("تسليم", res.data["detail"])

    def test_edit_blocked_after_delivery(self):
        txn_id = self._accepted()
        self.client.post(f"/api/office/transactions/{txn_id}/deliver/")
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/edit/", {"amount": "900"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_no_undo_delivery_at_all(self):
        """التسليم نهائي مطلق: لا تراجع ولا إعادة تعليم — الزبون استلم وذهب."""
        txn_id = self._accepted()
        self.client.post(f"/api/office/transactions/{txn_id}/deliver/")
        # محاولة تراجع (delivered=False) أو إعادة تعليم — كلها مرفوضة والحالة لا تتغير
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/deliver/", {"delivered": False}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        res = self.client.post(f"/api/office/transactions/{txn_id}/deliver/")
        self.assertEqual(res.status_code, 400)
        res = self.client.get(f"/api/office/transactions/history/")
        row = next(t for t in res.data if t["id"] == txn_id)
        self.assertEqual(row["delivery_status"], "delivered")

    def test_deliver_requires_accepted(self):
        self.auth("aleppo")
        txn_id = self.send_txn().data["id"]
        self.auth("damascus")
        res = self.client.post(f"/api/office/transactions/{txn_id}/deliver/")
        self.assertEqual(res.status_code, 400)


class PermissionTests(BaseTxnTestCase):
    def test_small_cannot_process(self):
        """الجزء 3: الصغير لا يعدّل ولا يعالج — ولا حتى قيد الانتظار."""
        self.auth("aleppo")
        txn_id = self.send_txn().data["id"]
        for action in ("approve", "reject", "pay", "deliver", "reverse"):
            res = self.client.post(f"/api/office/transactions/{txn_id}/{action}/")
            self.assertEqual(res.status_code, 403, action)

    def test_small_sees_only_own(self):
        create_small_office(tenant=self.tenant, name="آخر", username="other_s", password=PASSWORD)
        self.auth("aleppo")
        self.send_txn()
        self.auth("other_s")
        res = self.client.get("/api/my/transactions/")
        self.assertEqual(len(res.data), 0)


class PackageLimitTests(BaseTxnTestCase):
    def test_transactions_limit_enforced_with_grandfathering(self):
        from apps.admin_panel.models import Package, Subscription
        from apps.admin_panel.services import activate_subscription
        from apps.core.models import PlatformSettings

        # حركة قديمة في الوضع المجاني
        self.auth("aleppo")
        self.send_txn()

        s = PlatformSettings.load()
        s.free_mode = False
        s.save()
        pkg = Package.objects.create(
            name="ضيقة", max_small_offices=10, max_transactions=2, price=D("10")
        )
        sub = Subscription.objects.create(tenant=self.tenant, package=pkg)
        activate_subscription(sub, admin_user=None)

        # القديمة مُرحّلة — حدّ 2 يسمح باثنتين جديدتين
        self.assertEqual(self.send_txn().status_code, 201)
        self.assertEqual(self.send_txn().status_code, 201)
        res = self.send_txn()
        self.assertEqual(res.status_code, 400)
        self.assertIn("حد الباقة", res.data["detail"])


class FiltersTests(BaseTxnTestCase):
    def test_history_filters(self):
        self.auth("aleppo")
        a = self.send_txn(destination="دمشق").data["id"]
        b = self.send_txn(destination="بيروت").data["id"]
        self.auth("damascus")
        self.client.post(
            f"/api/office/transactions/{a}/approve/",
            {"box": self.box.pk, "fee_cost": "1", "fee_charged": "2"},
            format="json",
        )
        self.client.post(f"/api/office/transactions/{b}/reject/")

        res = self.client.get("/api/office/transactions/history/?approval=accepted")
        self.assertEqual(len(res.data), 1)
        res = self.client.get("/api/office/transactions/history/?q=بيروت")
        self.assertEqual(len(res.data), 1)
        res = self.client.get("/api/office/transactions/pending/")
        self.assertEqual(len(res.data), 0)


class PolishTests(BaseTxnTestCase):
    """المرحلة 10: تعديل الحركة من النقطة + تنبيه اقتراب الحد."""

    def _accepted(self, amount="1000"):
        self.auth("aleppo")
        txn_id = self.send_txn(amount=amount).data["id"]
        self.auth("damascus")
        self.client.post(
            f"/api/office/transactions/{txn_id}/approve/",
            {"box": self.box.pk, "fee_cost": "10", "fee_charged": "15"},
            format="json",
        )
        return txn_id

    def test_edit_endpoint_reverses_and_reposts(self):
        from apps.boxes.services import get_small_office_account

        txn_id = self._accepted()
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/edit/",
            {"fee_charged": "25"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(D(res.data["fee_charged"]), D("25"))
        with tenant_context(self.tenant):
            # الرصيد الجديد يعكس المستحقة المعدّلة: 1000+25
            self.assertEqual(get_small_office_account(self.small, "USD").balance, D("1025"))

    def test_edit_notifies_small(self):
        from apps.notifications.models import Notification

        txn_id = self._accepted()
        self.client.post(
            f"/api/office/transactions/{txn_id}/edit/",
            {"fee_charged": "20"},
            format="json",
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.small, title__contains="عُدّلت").exists()
        )

    def test_small_cannot_edit(self):
        txn_id = self._accepted()
        self.auth("aleppo")
        res = self.client.post(
            f"/api/office/transactions/{txn_id}/edit/",
            {"fee_charged": "1"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_limit_proximity_notification(self):
        from apps.boxes.models import CreditLimit
        from apps.notifications.models import Notification

        with tenant_context(self.tenant):
            CreditLimit.objects.filter(user=self.small, currency="USD").update(
                negative_limit=D("1200")
            )
        # 1000+15=1015 عليه ≥ 80% من 1200 (960) → تنبيه
        self._accepted()
        self.assertTrue(
            Notification.objects.filter(recipient=self.big, ntype=Notification.Type.LIMIT).exists()
        )
