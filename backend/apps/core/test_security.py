"""
حوالات — المسح الأمني الشامل (المرحلة 11)
=============================================
اختبارات عابرة للنظام كله: مسح 401/403، إبطال الخروج، تحديد المعدّل،
الثابت المحاسبي الكلي، واكتمال سجل التدقيق.
"""

from decimal import Decimal

from django.test import override_settings
from django.urls import reverse as url
from rest_framework.test import APITestCase

from apps.accounts.services import create_big_office, create_small_office
from apps.boxes.models import Currency, IntermediaryBox
from apps.core.models import AuditLog, JournalLine
from apps.core.tenancy import tenant_context

D = Decimal
PASSWORD = "secret12345"

# نقاط تتطلب توثيقاً — مسح 401 للمجهول
PROTECTED_GET = [
    "/api/auth/me/",
    "/api/notifications/",
    "/api/office/transactions/pending/",
    "/api/office/members/",
    "/api/office/boxes/",
    "/api/office/currencies/",
    "/api/office/reports/types/",
    "/api/office/whatsapp/",
    "/api/small/balances/",
    "/api/admin/stats/",
]

# نقاط الكبير — يجب أن تكون 403 على الصغير
OFFICE_ONLY_GET = [
    "/api/office/transactions/pending/",
    "/api/office/transactions/history/",
    "/api/office/members/",
    "/api/office/boxes/",
    "/api/office/credit-limits/",
    "/api/office/shop-cash/",
    "/api/office/whatsapp/",
    "/api/office/whatsapp/outbox/",
    "/api/office/alerts/",
    "/api/office/subscription/",
    "/api/office/reports/types/",
]


class BaseSecTestCase(APITestCase):
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

    def login(self, username):
        return self.client.post(
            url("auth-login"), {"username": username, "password": PASSWORD}, format="json"
        )

    def auth(self, username):
        res = self.login(username)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res


class SweepTests(BaseSecTestCase):
    def test_anonymous_sweep_401(self):
        """كل النقاط المحمية ترفض المجهول."""
        for path in PROTECTED_GET:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 401, path)

    def test_small_office_sweep_403_on_office_endpoints(self):
        """الصغير ممنوع من كل نقاط الكبير."""
        self.auth("aleppo")
        for path in OFFICE_ONLY_GET:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 403, path)

    def test_admin_cannot_reach_financial_endpoints(self):
        """الأدمن إداري بحت — كل النقاط المالية ترفضه."""
        from apps.accounts.models import User

        User.objects.create_user(username="admin1", password=PASSWORD, role=User.Role.ADMIN)
        self.auth("admin1")
        for path in OFFICE_ONLY_GET + ["/api/small/balances/"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 403, path)


class LogoutInvalidationTests(BaseSecTestCase):
    def test_logout_blacklists_refresh(self):
        """الخروج يُبطل refresh نهائياً — لا يمكن تجديد الجلسة بعده."""
        res = self.auth("damascus")
        refresh = res.data["refresh"]
        out = self.client.post(url("auth-logout"), {"refresh": refresh}, format="json")
        self.assertEqual(out.status_code, 200)
        renew = self.client.post(url("auth-refresh"), {"refresh": refresh}, format="json")
        self.assertEqual(renew.status_code, 401)

    def test_rotation_blacklists_old_refresh(self):
        """التدوير: استخدام refresh القديم بعد التجديد مرفوض."""
        res = self.auth("damascus")
        old = res.data["refresh"]
        first = self.client.post(url("auth-refresh"), {"refresh": old}, format="json")
        self.assertEqual(first.status_code, 200)
        again = self.client.post(url("auth-refresh"), {"refresh": old}, format="json")
        self.assertEqual(again.status_code, 401)


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": (
            "apps.accounts.authentication.BlockAwareJWTAuthentication",
        ),
        "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
        "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
        "DEFAULT_THROTTLE_RATES": {"login": "3/min", "register": "2/min", "authed": "1000/min"},
    }
)
class ThrottleTests(BaseSecTestCase):
    def test_login_throttled_after_limit(self):
        """محاولات دخول متكررة → 429 (حماية من التخمين)."""
        from unittest.mock import patch

        from django.core.cache import cache
        from rest_framework.throttling import ScopedRateThrottle

        from apps.accounts.views import LoginView

        cache.clear()
        # throttle_classes تُثبَّت وقت الاستيراد (معطّلة في بيئة الاختبار) — نرقّعها هنا
        patcher = patch.object(LoginView, "throttle_classes", [ScopedRateThrottle])
        patcher.start()
        self.addCleanup(patcher.stop)
        for _ in range(3):
            self.client.post(
                url("auth-login"), {"username": "damascus", "password": "wrong"}, format="json"
            )
        res = self.client.post(
            url("auth-login"), {"username": "damascus", "password": PASSWORD}, format="json"
        )
        self.assertEqual(res.status_code, 429)


class GlobalLedgerInvariantTests(BaseSecTestCase):
    def test_debits_equal_credits_after_mixed_operations(self):
        """الثابت الكلي (ق3): مجموع المدين = مجموع الدائن على مستوى النظام كله."""
        from django.db.models import Sum

        self.auth("damascus")
        self.client.post(
            "/api/office/credit-limits/",
            {"user": self.small.pk, "currency": "USD", "negative_limit": "100000"},
            format="json",
        )
        # اعتماد + حركة مقبولة + قبض + سحب + عكس
        self.client.post(
            f"/api/office/boxes/{self.box.pk}/deposit/",
            {"small_user": self.small.pk, "currency": "USD", "amount": "2000"},
            format="json",
        )
        self.auth("aleppo")
        txn = self.client.post(
            "/api/my/transactions/",
            {
                "sender": "أ",
                "beneficiary": "ب",
                "amount": "1000",
                "currency_received": "USD",
                "currency_delivered": "USD",
                "destination": "دمشق",
            },
            format="json",
        ).data
        self.auth("damascus")
        self.client.post(
            f"/api/office/transactions/{txn['id']}/approve/",
            {"box": self.box.pk, "fee_cost": "10", "fee_charged": "15"},
            format="json",
        )
        self.client.post(f"/api/office/transactions/{txn['id']}/pay/")
        self.client.post(
            f"/api/office/boxes/{self.box.pk}/withdraw/",
            {"small_user": self.small.pk, "currency": "USD", "amount": "300"},
            format="json",
        )
        self.client.post(f"/api/office/transactions/{txn['id']}/reverse/")

        agg = JournalLine.all_objects.aggregate(
            debit=Sum("debit", default=0), credit=Sum("credit", default=0)
        )
        self.assertEqual(agg["debit"], agg["credit"])
        self.assertGreater(agg["debit"], D("0"))


class AuditCompletenessTests(BaseSecTestCase):
    def test_actions_produce_audit_rows(self):
        """كل فعل جوهري يترك أثراً في سجل التدقيق."""
        self.auth("damascus")
        self.client.post(
            "/api/office/credit-limits/",
            {"user": self.small.pk, "currency": "USD", "negative_limit": "100000"},
            format="json",
        )
        self.client.post(
            f"/api/office/boxes/{self.box.pk}/deposit/",
            {"small_user": self.small.pk, "currency": "USD", "amount": "100"},
            format="json",
        )
        self.auth("aleppo")
        self.client.post(
            "/api/my/transactions/",
            {
                "sender": "أ",
                "beneficiary": "ب",
                "amount": "50",
                "currency_received": "USD",
                "currency_delivered": "USD",
                "destination": "دمشق",
            },
            format="json",
        )
        self.auth("damascus")
        self.client.post(f"/api/office/members/{self.small.pk}/block/")

        actions = set(AuditLog.objects.values_list("action", flat=True))
        for expected in ("set_credit_limit", "deposit", "create_transaction", "block_member"):
            self.assertIn(expected, actions)
