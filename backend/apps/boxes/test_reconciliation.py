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
            self.usd = Currency.objects.create(code="USD", name="دولار")
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

    def test_small_reconciles_self(self):
        deposit_to_box(
            tenant=self.tenant, box=self.box, small_user=self.small, currency="USD", amount=D("100")
        )
        self.auth("aleppo")
        res = self.client.get("/api/small/reconciliation/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(D(res.data["rows"][0]["balance"]), D("-100"))
        res = self.client.post("/api/small/reconciliation/")
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
        self.assertEqual(D(res.data["balance"]), D("-300"))
        self.assertEqual(len(res.data["lines"]), 1)

        self.auth("aleppo")
        res = self.client.get("/api/small/statement/?currency=USD")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(D(res.data["balance"]), D("-300"))
