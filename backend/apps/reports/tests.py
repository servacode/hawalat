"""حوالات — اختبارات التقارير والتصدير (المرحلة 7)."""

from decimal import Decimal

from django.urls import reverse as url
from rest_framework.test import APITestCase

from apps.accounts.services import create_big_office, create_small_office
from apps.boxes.models import Currency, IntermediaryBox
from apps.core.tenancy import tenant_context

D = Decimal
PASSWORD = "secret12345"


class BaseReportsTestCase(APITestCase):
    def setUp(self):
        self.big = create_big_office(name="مكتب دمشق", username="damascus", password=PASSWORD)
        self.tenant = self.big.tenant
        self.small = create_small_office(
            tenant=self.tenant, name="مكتب حلب", username="aleppo", password=PASSWORD
        )
        with tenant_context(self.tenant):
            usd = Currency.objects.get(code="USD")
            self.box = IntermediaryBox.objects.create(name="الوعد", number="101")
            self.box.currencies.add(usd)
        self.auth("damascus")
        self.client.post(
            "/api/office/credit-limits/",
            {"user": self.small.pk, "currency": "USD", "negative_limit": "100000"},
            format="json",
        )

    def auth(self, username):
        res = self.client.post(
            url("auth-login"), {"username": username, "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def make_accepted(self, amount="1000", cost="10", charged="15"):
        self.auth("aleppo")
        txn = self.client.post(
            "/api/my/transactions/",
            {
                "sender": "أ",
                "beneficiary": "ب",
                "amount": amount,
                "currency_received": "USD",
                "currency_delivered": "USD",
                "destination": "دمشق",
            },
            format="json",
        ).data
        self.auth("damascus")
        self.client.post(
            f"/api/office/transactions/{txn['id']}/approve/",
            {"box": self.box.pk, "fee_cost": cost, "fee_charged": charged},
            format="json",
        )
        return txn


class ProfitReportTests(BaseReportsTestCase):
    def test_profit_is_fee_margin(self):
        """الربح = المستحقة − رأس المال (حركتان: 5+3=8)."""
        self.make_accepted(cost="10", charged="15")
        self.make_accepted(cost="7", charged="10")
        self.auth("damascus")
        res = self.client.get("/api/office/reports/?type=profits")
        self.assertEqual(res.status_code, 200)
        row = res.data["rows"][0]
        self.assertEqual(row[0], "USD")
        self.assertEqual(D(row[1]), D("2"))  # عدد
        self.assertEqual(D(row[4]), D("8"))  # الربح

    def test_date_filter_excludes(self):
        self.make_accepted()
        self.auth("damascus")
        res = self.client.get("/api/office/reports/?type=profits&date_from=2030-01-01")
        self.assertEqual(res.data["rows"], [])

    def test_by_status_counts(self):
        self.make_accepted()
        self.auth("damascus")
        res = self.client.get("/api/office/reports/?type=by_status")
        rows = {(r[0], r[1]): r[2] for r in res.data["rows"]}
        self.assertEqual(rows[("القبول", "مقبولة")], "1")
        self.assertEqual(rows[("القبول", "قيد الانتظار")], "0")


class ScopeTests(BaseReportsTestCase):
    def test_small_sees_only_allowed_types(self):
        self.auth("aleppo")
        res = self.client.get("/api/small/reports/types/")
        types = [t["type"] for t in res.data]
        self.assertIn("summary", types)
        self.assertNotIn("profits", types)  # الأرباح للكبير فقط

    def test_small_denied_big_report(self):
        self.auth("aleppo")
        res = self.client.get("/api/small/reports/?type=profits")
        self.assertEqual(res.status_code, 403)

    def test_small_activity_scoped_to_self(self):
        self.make_accepted()
        create_small_office(tenant=self.tenant, name="آخر", username="other2", password=PASSWORD)
        self.auth("aleppo")
        res = self.client.get("/api/small/reports/?type=activity")
        self.assertEqual(D(res.data["rows"][0][1]), D("1"))

    def test_big_cannot_use_small_scope(self):
        self.auth("damascus")
        res = self.client.get("/api/small/reports/?type=summary")
        self.assertEqual(res.status_code, 403)


class ExportTests(BaseReportsTestCase):
    def test_xlsx_export(self):
        self.make_accepted()
        self.auth("damascus")
        res = self.client.get("/api/office/reports/?type=profits&export=xlsx")
        self.assertEqual(res.status_code, 200)
        self.assertIn("spreadsheetml", res["Content-Type"])
        self.assertGreater(len(res.content), 4000)
        self.assertTrue(res.content[:2] == b"PK")  # zip/xlsx

    def test_pdf_export_arabic(self):
        self.make_accepted()
        self.auth("damascus")
        res = self.client.get("/api/office/reports/?type=profits&export=pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))
        self.assertGreater(len(res.content), 5000)  # يتضمن الخط المضمّن

    def test_unknown_type_lists_available(self):
        self.auth("damascus")
        res = self.client.get("/api/office/reports/?type=nope")
        self.assertEqual(res.status_code, 400)
        self.assertGreaterEqual(len(res.data["available"]), 13)
