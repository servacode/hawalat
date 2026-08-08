"""
حوالات — اختبارات النواة المحاسبية (المرحلة 4)
==================================================
تفحص: المشهد 5 (اعتماد/سحب)، رياضيات الحد السالب، عكس القيد عبر API،
العزل بين المستأجرين، الكشوف، وأرصدة المكتب الصغير.
"""

from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.services import create_big_office, create_small_office
from apps.core.tenancy import tenant_context

from .models import Currency, IntermediaryBox
from .services import (
    check_credit_limit,
    deposit_to_box,
    get_small_office_account,
    withdraw_from_box,
)

D = Decimal
PASSWORD = "secret12345"


class DefaultCurrenciesTests(APITestCase):
    """العملات المتفق عليها (دولار/يورو/تركي/سوري) تُزرع تلقائياً لكل مكتب كبير جديد."""

    def test_big_office_gets_default_currencies(self):
        big = create_big_office(name="مكتب اختبار", username="curr_test", password=PASSWORD)
        with tenant_context(big.tenant):
            codes = set(Currency.objects.values_list("code", flat=True))
        self.assertEqual(codes, {"USD", "EUR", "TRY", "SYP"})

    def test_seeding_is_isolated_per_tenant(self):
        big1 = create_big_office(name="مكتب 1", username="curr_t1", password=PASSWORD)
        big2 = create_big_office(name="مكتب 2", username="curr_t2", password=PASSWORD)
        with tenant_context(big1.tenant):
            self.assertEqual(Currency.objects.count(), 4)
        with tenant_context(big2.tenant):
            self.assertEqual(Currency.objects.count(), 4)


class BaseBoxesTestCase(APITestCase):
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
            reverse("auth-login"),
            {"username": username, "password": PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")


class SettlementTests(BaseBoxesTestCase):
    """المشهد 5 حرفياً: الاعتماد يزيد الصندوق ويُنقص ما على الصغير، والسحب عكسه."""

    def test_deposit_effects(self):
        entry = deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("2000"),
        )
        with tenant_context(self.tenant):
            from .services import get_box_account

            self.assertEqual(get_box_account(self.box, "USD").balance, D("2000"))
            self.assertEqual(get_small_office_account(self.small, "USD").balance, D("-2000"))
        self.assertEqual(entry.lines.count(), 2)

    def test_withdraw_effects(self):
        deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("2000"),
        )
        withdraw_from_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("500"),
        )
        with tenant_context(self.tenant):
            from .services import get_box_account

            self.assertEqual(get_box_account(self.box, "USD").balance, D("1500"))
            self.assertEqual(get_small_office_account(self.small, "USD").balance, D("-1500"))

    def test_currency_not_in_box_rejected(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            deposit_to_box(
                tenant=self.tenant,
                box=self.box,
                small_user=self.small,
                currency="EUR",
                amount=D("100"),
            )

    def test_negative_amount_rejected(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            deposit_to_box(
                tenant=self.tenant,
                box=self.box,
                small_user=self.small,
                currency="USD",
                amount=D("-5"),
            )


class CreditLimitTests(BaseBoxesTestCase):
    """الجزء 5: الحد −5000 → عند بلوغه يُمنع ويُطلب تعزيز الرصيد."""

    def test_zero_limit_blocks_any_debt(self):
        ok, reason = check_credit_limit(self.small, "USD", D("1"))
        self.assertFalse(ok)
        self.assertIn("تعزيز", reason)

    def test_limit_allows_up_to_and_blocks_beyond(self):
        self.auth("damascus")
        res = self.client.post(
            "/api/office/credit-limits/",
            {"user": self.small.pk, "currency": "USD", "negative_limit": "5000"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)

        ok, _ = check_credit_limit(self.small, "USD", D("5000"))
        self.assertTrue(ok)
        ok, _ = check_credit_limit(self.small, "USD", D("5001"))
        self.assertFalse(ok)

    def test_deposit_frees_capacity(self):
        """تعزيز الرصيد يفتح المجال من جديد — الدورة §6."""
        self.auth("damascus")
        self.client.post(
            "/api/office/credit-limits/",
            {"user": self.small.pk, "currency": "USD", "negative_limit": "1000"},
            format="json",
        )
        # عليه 1000 (بحد 1000) → ممتلئ
        withdraw_from_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("1000"),
        )
        ok, _ = check_credit_limit(self.small, "USD", D("1"))
        self.assertFalse(ok)
        # اعتماد 600 → عليه 400 → متاح 600
        deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("600"),
        )
        ok, _ = check_credit_limit(self.small, "USD", D("600"))
        self.assertTrue(ok)
        ok, _ = check_credit_limit(self.small, "USD", D("601"))
        self.assertFalse(ok)


class ApiFlowTests(BaseBoxesTestCase):
    def test_big_office_full_flow_via_api(self):
        self.auth("damascus")
        # إنشاء عملة وصندوق عبر الـ API
        res = self.client.post(
            "/api/office/currencies/", {"code": "KWD", "name": "دينار كويتي"}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        res = self.client.post(
            "/api/office/boxes/",
            {"name": "الفجر", "number": "102", "currencies": ["KWD", "USD"]},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        box_id = res.data["id"]

        # اعتماد عبر الـ API
        res = self.client.post(
            f"/api/office/boxes/{box_id}/deposit/",
            {"small_user": self.small.pk, "currency": "KWD", "amount": "3000"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        entry_id = res.data["entry_id"]

        # كشف الصندوق
        res = self.client.get(f"/api/office/boxes/{box_id}/statement/?currency=KWD")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(D(res.data["balance"]), D("3000"))
        self.assertEqual(len(res.data["lines"]), 1)

        # عكس القيد عبر الـ API → يعود الرصيد صفراً
        res = self.client.post(f"/api/office/entries/{entry_id}/reverse/")
        self.assertEqual(res.status_code, 201)
        res = self.client.get(f"/api/office/boxes/{box_id}/statement/?currency=KWD")
        self.assertEqual(D(res.data["balance"]), D("0"))

    def test_small_office_sees_own_balances(self):
        deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("250"),
        )
        self.auth("aleppo")
        res = self.client.get("/api/small/balances/")
        self.assertEqual(res.status_code, 200)
        row = res.data["balances"][0]
        self.assertEqual(row["currency"], "USD")
        self.assertEqual(D(row["owed_to_me"]), D("250"))  # له (دفع مقدماً)
        self.assertEqual(row["owed_by_me"], "0")

    def test_small_office_cannot_manage_boxes(self):
        self.auth("aleppo")
        for url in ["/api/office/currencies/", "/api/office/boxes/", "/api/office/credit-limits/"]:
            self.assertEqual(self.client.get(url).status_code, 403, url)


class TenantIsolationBoxesTests(BaseBoxesTestCase):
    """ق2: مستأجر آخر لا يرى صناديق/عملات/تسويات غيره."""

    def setUp(self):
        super().setUp()
        self.other_big = create_big_office(name="مكتب آخر", username="otherbig", password=PASSWORD)
        with tenant_context(self.tenant):
            Currency.objects.create(code="KWD", name="دينار كويتي")

    def test_other_tenant_sees_only_own_currencies_and_boxes(self):
        self.auth("otherbig")
        res = self.client.get("/api/office/currencies/")
        codes = [c["code"] for c in (res.data.get("results") or res.data)]
        # يرى عملاته الافتراضية الأربع فقط — ولا يرى KWD المضافة عند المستأجر الآخر
        self.assertEqual(sorted(codes), ["EUR", "SYP", "TRY", "USD"])
        self.assertNotIn("KWD", codes)

        res = self.client.get("/api/office/boxes/")
        boxes = res.data.get("results", res.data)
        self.assertEqual(list(boxes), [])

    def test_cannot_settle_on_foreign_small_office(self):
        self.auth("otherbig")
        with tenant_context(self.other_big.tenant):
            eur = Currency.objects.get(code="EUR")
            box = IntermediaryBox.objects.create(name="غريب", number="900")
            box.currencies.add(eur)
        res = self.client.post(
            f"/api/office/boxes/{box.pk}/deposit/",
            {"small_user": self.small.pk, "currency": "EUR", "amount": "100"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("ضمن مكتبك", res.data["detail"])

    def test_cannot_reverse_foreign_entry(self):
        entry = deposit_to_box(
            tenant=self.tenant,
            box=self.box,
            small_user=self.small,
            currency="USD",
            amount=D("100"),
        )
        self.auth("otherbig")
        res = self.client.post(f"/api/office/entries/{entry.pk}/reverse/")
        self.assertEqual(res.status_code, 404)  # معزول — لا يراه أصلاً
