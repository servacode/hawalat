"""
حوالات — اختبارات وحدة الأدمن (المرحلة 3)
============================================
تفحص: حراسة RBAC، دورة الاشتراك (طلب→تفعيل)، قاعدة الترحيل، حظر المكتب
المفروض على كل طلب، الإحصاءات غير المالية، والبث.
"""

from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.services import create_big_office, create_small_office
from apps.core.models import PlatformSettings

from .models import Package, Subscription
from .services import can_create_small_office

PASSWORD = "secret12345"


class BaseAdminTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password=PASSWORD, role=User.Role.ADMIN
        )
        self.big = create_big_office(name="مكتب دمشق", username="damascus", password=PASSWORD)
        self.package = Package.objects.create(
            name="أساسية",
            max_small_offices=2,
            max_transactions=100,
            price=Decimal("50"),
        )

    def auth(self, username):
        res = self.client.post(
            reverse("auth-login"),
            {"username": username, "password": PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res


class RBACGuardTests(BaseAdminTestCase):
    """ق4: نقاط الأدمن للأدمن فقط، ونقاط المكتب للمكتب فقط."""

    def test_big_office_cannot_access_admin_endpoints(self):
        self.auth("damascus")
        for url in [
            "/api/admin/offices/",
            "/api/admin/packages/",
            "/api/admin/stats/",
            "/api/admin/settings/",
            "/api/admin/audit/",
        ]:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 403, url)

    def test_admin_cannot_access_office_endpoints(self):
        self.auth("admin")
        res = self.client.get("/api/office/subscription/")
        self.assertEqual(res.status_code, 403)

    def test_anonymous_rejected(self):
        res = self.client.get("/api/admin/stats/")
        self.assertEqual(res.status_code, 401)


class BigOfficeManagementTests(BaseAdminTestCase):
    def test_admin_creates_big_office_with_generated_code(self):
        self.auth("admin")
        res = self.client.post(
            "/api/admin/offices/",
            {"name": "مكتب حلب", "username": "aleppo_big", "password": PASSWORD, "phone": "+90"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["code"], "BIG002")
        self.assertEqual(res.data["owner_username"], "aleppo_big")

    def test_block_prevents_all_requests_for_tenant_users(self):
        """حظر المكتب يقطع الوصول فوراً حتى مع توكن صالح."""
        login = self.client.post(
            reverse("auth-login"),
            {"username": "damascus", "password": PASSWORD},
            format="json",
        )
        big_token = login.data["access"]

        self.auth("admin")
        res = self.client.post(f"/api/admin/offices/{self.big.tenant_id}/block/")
        self.assertEqual(res.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {big_token}")
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, 401)

        # فك الحظر يعيد الوصول
        self.auth("admin")
        self.client.post(f"/api/admin/offices/{self.big.tenant_id}/unblock/")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {big_token}")
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 200)

    def test_admin_offices_list_has_no_financial_fields(self):
        self.auth("admin")
        res = self.client.get("/api/admin/offices/")
        self.assertEqual(res.status_code, 200)
        row = res.data[0]
        for forbidden in ("balance", "debit", "credit", "amount"):
            self.assertNotIn(forbidden, row)


class SubscriptionFlowTests(BaseAdminTestCase):
    def test_full_flow_request_then_activate(self):
        # المكتب يطلب
        self.auth("damascus")
        res = self.client.post(
            "/api/office/subscription/", {"package": self.package.pk}, format="json"
        )
        self.assertEqual(res.status_code, 201)
        sub_id = res.data["id"]
        self.assertEqual(res.data["status"], "pending")

        # لا يستطيع طلب ثانٍ وطلبه معلق
        dup = self.client.post(
            "/api/office/subscription/", {"package": self.package.pk}, format="json"
        )
        self.assertEqual(dup.status_code, 400)

        # الأدمن يفعّل بعد الدفع اليدوي
        self.auth("admin")
        res = self.client.post(f"/api/admin/subscriptions/{sub_id}/activate/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "active")
        self.assertIsNotNone(res.data["expires_at"])

    def test_cannot_activate_twice(self):
        sub = Subscription.objects.create(tenant=self.big.tenant, package=self.package)
        self.auth("admin")
        self.client.post(f"/api/admin/subscriptions/{sub.pk}/activate/")
        res = self.client.post(f"/api/admin/subscriptions/{sub.pk}/activate/")
        self.assertEqual(res.status_code, 400)


class GrandfatheringTests(BaseAdminTestCase):
    """المشهد 1: مكاتب الوضع المجاني لا تُحتسب على حد الباقة."""

    def _make_smalls(self, n, prefix):
        for i in range(n):
            create_small_office(
                tenant=self.big.tenant,
                name=f"صغير {prefix}{i}",
                username=f"s_{prefix}{i}",
                password=PASSWORD,
            )

    def test_free_mode_unlimited(self):
        self._make_smalls(5, "free")
        ok, _ = can_create_small_office(self.big.tenant)
        self.assertTrue(ok)

    def test_paid_mode_requires_subscription(self):
        s = PlatformSettings.load()
        s.free_mode = False
        s.save()
        ok, reason = can_create_small_office(self.big.tenant)
        self.assertFalse(ok)
        self.assertIn("اشتراك", reason)

    def test_grandfathered_offices_not_counted(self):
        # 5 مكاتب أُنشئت في الوضع المجاني (قبل التفعيل)
        self._make_smalls(5, "old")

        # تفعيل الوضع المدفوع + اشتراك بحد 2
        s = PlatformSettings.load()
        s.free_mode = False
        s.save()
        sub = Subscription.objects.create(tenant=self.big.tenant, package=self.package)
        from .services import activate_subscription

        activate_subscription(sub, admin_user=self.admin)

        # القديمة (5) تتجاوز الحد (2) لكنها مرحّلة — يُسمح بالإنشاء
        ok, _ = can_create_small_office(self.big.tenant)
        self.assertTrue(ok)

        # بعد إنشاء 2 جديدة (بعد التفعيل) يُبلغ الحد
        self._make_smalls(2, "new")
        ok, reason = can_create_small_office(self.big.tenant)
        self.assertFalse(ok)
        self.assertIn("حد الباقة", reason)


class StatsAndBroadcastTests(BaseAdminTestCase):
    def test_stats_shape(self):
        create_small_office(tenant=self.big.tenant, name="ص", username="s1", password=PASSWORD)
        self.auth("admin")
        res = self.client.get("/api/admin/stats/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["big_offices_total"], 1)
        self.assertEqual(res.data["small_offices_total"], 1)
        # لا حقول مالية
        for forbidden in ("balance", "profit", "amount"):
            self.assertNotIn(forbidden, res.data)

    def test_admin_broadcast_visible_to_big_office(self):
        self.auth("admin")
        res = self.client.post(
            "/api/admin/broadcasts/",
            {"title": "صيانة", "message": "توقف مؤقت الليلة"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)

        self.auth("damascus")
        res = self.client.get("/api/office/broadcasts/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data[0]["title"], "صيانة")

    def test_settings_toggle(self):
        self.auth("admin")
        res = self.client.patch("/api/admin/settings/", {"free_mode": False}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(PlatformSettings.load().free_mode)

    def test_audit_records_admin_actions(self):
        self.auth("admin")
        self.client.post(f"/api/admin/offices/{self.big.tenant_id}/block/")
        res = self.client.get("/api/admin/audit/")
        actions = [row["action"] for row in res.data]
        self.assertIn("block_big_office", actions)
