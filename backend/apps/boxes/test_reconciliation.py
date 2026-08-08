"""
حوالات — اختبارات المطابقة وقسم الحسابات (المرحلة 6)
========================================================
"""

from decimal import Decimal

from django.urls import reverse as url
from rest_framework.test import APITestCase

from apps.accounts.services import create_big_office, create_small_office
from apps.boxes.models import Currency, IntermediaryBox
from apps.boxes.services import (
    build_reconciliation,
    deposit_to_box,
    get_small_office_account,
    withdraw_from_box,
)
from apps.core.tenancy import tenant_context

D = Decimal
PASSWORD = "secret12345"


class BaseRecTestCase(APITestCase):
    def setUp(self):
        self.big = create_big_office(name="مكتب دمشق", username="damascus", password=PASSWORD)
        self.tenant = self.big.tenant
        self.small = create_small_office(
            tenant=self.tenant, name="مكتب حلب", username="aleppo", password=PASSWORD
        )
        with tenant_context(self.tenant):
            self.usd = Currency.objects.get(code="USD")
            self.box = IntermediaryBox.objects.create(name="الوعد", number="101")
            self.box.currencies.add(self.usd)

    def auth(self, username):
        res = self.client.post(
            url("auth-login"), {"username": username, "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")


class ReconciliationLogicTests(BaseRecTestCase):
    """المشهد 4: كشف دوري تراكمي بنقطة إغلاق — لا تصفير."""

    def test_first_reconciliation_shows_all(self):
        deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("2000"),
        )
        data = build_reconciliation(self.small)
        self.assertIsNone(data["last_at"])
        row = data["rows"][0]
        self.assertEqual(D(row["previous"]), D("0"))
        self.assertEqual(D(row["balance"]), D("-2000"))  # له

    def test_checkpoint_behavior_previous_plus_delta(self):
        """بعد التثبيت: الفترة الجديدة تبدأ برصيد سابق + حركاتها فقط."""
        deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("2000"),
        )
        self.auth("damascus")
        res = self.client.post(f"/api/office/members/{self.small.pk}/reconciliation/")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(D(res.data["rows"][0]["balance"]), D("-2000"))

        # حركة جديدة بعد نقطة الإغلاق
        withdraw_from_box(
            tenant=self.tenant, box=self.box, small_user=self.small, currency="USD", amount=D("500")
        )

        res = self.client.get(f"/api/office/members/{self.small.pk}/reconciliation/")
        row = res.data["rows"][0]
        self.assertIsNotNone(res.data["last_at"])
        self.assertEqual(D(row["previous"]), D("-2000"))  # رصيد سابق
        self.assertEqual(D(row["debits"]), D("500"))  # حركات الفترة فقط
        self.assertEqual(D(row["credits"]), D("0"))
        self.assertEqual(D(row["balance"]), D("-1500"))

        # الثابت: السابق + مدين − دائن = رصيد الحساب الفعلي (تراكمي — لا تصفير)
        with tenant_context(self.tenant):
            actual = get_small_office_account(self.small, "USD").balance
        self.assertEqual(D(row["balance"]), actual)

    def test_small_view_and_pdf_only_never_commits(self):
        """ملاحظة التجربة 14: الصغير يشاهد المطابقة وينزّلها PDF فقط — لا يثبّت أبداً."""
        deposit_to_box(
            tenant=self.tenant, box=self.box, small_user=self.small, currency="USD", amount=D("100")
        )
        self.auth("aleppo")
        # المعاينة متاحة — والتثبيت ممنوع دائماً
        res = self.client.get("/api/small/reconciliation/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["allowed"])
        res = self.client.post("/api/small/reconciliation/")
        self.assertEqual(res.status_code, 403)

        # الكبير يثبّت — والصغير ينزّل سجلها PDF
        self.auth("damascus")
        rec_id = self.client.post(
            f"/api/office/members/{self.small.pk}/reconciliation/"
        ).data["id"]
        self.auth("aleppo")
        res = self.client.get(f"/api/small/reconciliations/{rec_id}/pdf/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))
        # ولا ينزّل سجل غيره
        self.assertEqual(self.client.get("/api/small/reconciliations/999999/pdf/").status_code, 404)

    def test_reconciliation_history_log(self):
        """ملاحظة التجربة 12: لكل مطابقة سجل بلقطة كاملة يُرجع إليه عند الخطأ."""
        deposit_to_box(
            tenant=self.tenant, box=self.box, small_user=self.small, currency="USD", amount=D("500")
        )
        self.auth("damascus")
        self.client.post(f"/api/office/members/{self.small.pk}/reconciliation/")
        deposit_to_box(
            tenant=self.tenant, box=self.box, small_user=self.small, currency="USD", amount=D("200")
        )
        self.client.post(f"/api/office/members/{self.small.pk}/reconciliation/")

        # الصغير يرى سجله كاملاً بالأحدث أولاً وبلقطة تفصيلية
        self.auth("aleppo")
        res = self.client.get("/api/small/reconciliations/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)
        latest = res.data[0]["rows"][0]
        for key in ("currency", "previous", "debits", "credits", "balance"):
            self.assertIn(key, latest)
        self.assertEqual(D(latest["previous"]), D("-500"))
        self.assertEqual(D(latest["balance"]), D("-700"))

        # الكبير يرى سجل عضوه — والغريب ممنوع
        self.auth("damascus")
        res = self.client.get(f"/api/office/members/{self.small.pk}/reconciliations/")
        self.assertEqual(len(res.data), 2)
        other_big = create_big_office(name="غريب", username="strb", password=PASSWORD)
        foreign = create_small_office(
            tenant=other_big.tenant, name="غ", username="strs", password=PASSWORD
        )
        res = self.client.get(f"/api/office/members/{foreign.pk}/reconciliations/")
        self.assertEqual(res.status_code, 403)

    def test_big_commits_member_reconciliation_regardless(self):
        """الكبير يثبّت مطابقة أعضائه دائماً — الصلاحية تخص الصغار فقط."""
        self.auth("damascus")
        res = self.client.post(f"/api/office/members/{self.small.pk}/reconciliation/")
        self.assertEqual(res.status_code, 201)

    def test_big_cannot_reconcile_foreign_member(self):
        other_big = create_big_office(name="آخر", username="ob", password=PASSWORD)
        foreign = create_small_office(
            tenant=other_big.tenant, name="غريب", username="fs", password=PASSWORD
        )
        self.auth("damascus")
        res = self.client.get(f"/api/office/members/{foreign.pk}/reconciliation/")
        self.assertEqual(res.status_code, 403)


class MembersTests(BaseRecTestCase):
    def test_retrieve_member_profile(self):
        self.auth("damascus")
        res = self.client.get(f"/api/office/members/{self.small.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["office_code"], self.small.office_code)

    def test_retrieve_foreign_member_denied(self):
        other_big = create_big_office(name="بعيد", username="farb", password=PASSWORD)
        foreign = create_small_office(
            tenant=other_big.tenant, name="بعيد ص", username="fars", password=PASSWORD
        )
        self.auth("damascus")
        res = self.client.get(f"/api/office/members/{foreign.pk}/")
        self.assertEqual(res.status_code, 404)

    def test_create_member_with_generated_code(self):
        self.auth("damascus")
        res = self.client.post(
            "/api/office/members/",
            {
                "name": "مكتب حمص",
                "username": "homs",
                "password": PASSWORD,
                "whatsapp_group_link": "https://chat.whatsapp.com/xyz",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["office_code"], "BIG001-SML002")

    def test_create_member_respects_package_limit(self):
        from apps.admin_panel.models import Package, Subscription
        from apps.admin_panel.services import activate_subscription
        from apps.core.models import PlatformSettings

        s = PlatformSettings.load()
        s.free_mode = False
        s.save()
        pkg = Package.objects.create(
            name="ضيقة", max_small_offices=1, max_transactions=10, price=D("5")
        )
        sub = Subscription.objects.create(tenant=self.tenant, package=pkg)
        activate_subscription(sub, admin_user=None)

        self.auth("damascus")
        ok = self.client.post(
            "/api/office/members/",
            {"name": "أ", "username": "m1", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(ok.status_code, 201)
        denied = self.client.post(
            "/api/office/members/",
            {"name": "ب", "username": "m2", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertIn("حد الباقة", denied.data["detail"])

    def test_block_member_stops_access(self):
        self.auth("aleppo")
        me = self.client.get(url("auth-me"))
        self.assertEqual(me.status_code, 200)
        token_small = self.client._credentials["HTTP_AUTHORIZATION"]

        self.auth("damascus")
        res = self.client.post(f"/api/office/members/{self.small.pk}/block/")
        self.assertEqual(res.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=token_small)
        self.assertEqual(self.client.get(url("auth-me")).status_code, 401)

    def test_member_statement_and_small_statement(self):
        deposit_to_box(
            tenant=self.tenant, box=self.box, small_user=self.small, currency="USD", amount=D("300")
        )
        self.auth("damascus")
        res = self.client.get(f"/api/office/members/{self.small.pk}/statement/?currency=USD")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["lines"]), 1)
        self.assertEqual(res.data["lines"][0]["currency"], "USD")

        # بلا عملة = كل الحركات بكل العملات (ملاحظة 52) + فلتر الفترة يعمل
        res = self.client.get(f"/api/office/members/{self.small.pk}/statement/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["lines"]), 1)
        res = self.client.get(
            f"/api/office/members/{self.small.pk}/statement/?date_from=2030-01-01"
        )
        self.assertEqual(len(res.data["lines"]), 0)

        # دفعة نقدية يدوية (ملاحظة 54): تدخل المحل وتُنقص ما عليه — والملاحظة إلزامية
        no_memo = self.client.post(
            "/api/office/shop-cash/payments/",
            {"member": self.small.pk, "currency": "USD", "amount": "100"},
            format="json",
        )
        self.assertEqual(no_memo.status_code, 400)
        ok = self.client.post(
            "/api/office/shop-cash/payments/",
            {"member": self.small.pk, "currency": "USD", "amount": "100", "memo": "دفعة بيد أحمد"},
            format="json",
        )
        self.assertEqual(ok.status_code, 201)
        from .services import get_shop_cash_account, get_small_office_account

        self.assertEqual(get_shop_cash_account(self.tenant, "USD").balance, D("100"))
        self.assertEqual(get_small_office_account(self.small, "USD").balance, D("-400"))

        self.auth("aleppo")
        res = self.client.get("/api/small/statement/?currency=USD")
        self.assertEqual(res.status_code, 200)
        # 300 اعتماد + 100 دفعة نقدية = 400 له
        self.assertEqual(D(res.data["balance"]), D("-400"))
