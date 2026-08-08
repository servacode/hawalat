"""
حوالات — اختبارات المصادقة والهوية (المرحلة 2)
================================================
تفحص: الدخول الموحّد وclaims الدور، تذكّرني، الحظر، الاستعادة الهرمية
بعزل صارم، التسجيل الذاتي خلف المفتاح، وصيَغ الأكواد الفريدة.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import PlatformSettings, Tenant

from .models import User
from .services import (
    create_big_office,
    create_small_office,
    generate_big_office_code,
    generate_small_office_code,
)


class CodeGenerationTests(TestCase):
    """المشهد 6: أكواد فريدة، وكود الصغير يحمل كود مكتبه الكبير."""

    def test_big_codes_sequence(self):
        self.assertEqual(generate_big_office_code(), "BIG001")
        Tenant.objects.create(name="أ", code="BIG001")
        Tenant.objects.create(name="ب", code="BIG007")
        self.assertEqual(generate_big_office_code(), "BIG008")

    def test_small_code_carries_big_code(self):
        big = create_big_office(name="مكتب دمشق", username="damascus", password="secret123")
        s1 = create_small_office(
            tenant=big.tenant, name="حلب", username="aleppo", password="secret123"
        )
        s2 = create_small_office(
            tenant=big.tenant, name="حمص", username="homs", password="secret123"
        )
        self.assertEqual(s1.office_code, f"{big.tenant.code}-SML001")
        self.assertEqual(s2.office_code, f"{big.tenant.code}-SML002")

    def test_small_sequences_isolated_per_tenant(self):
        b1 = create_big_office(name="أ", username="b1", password="secret123")
        b2 = create_big_office(name="ب", username="b2", password="secret123")
        create_small_office(tenant=b1.tenant, name="س1", username="s1", password="secret123")
        s_other = create_small_office(
            tenant=b2.tenant, name="س2", username="s2", password="secret123"
        )
        # تسلسل كل مستأجر مستقل ويبدأ من 001
        self.assertEqual(s_other.office_code, f"{b2.tenant.code}-SML001")

    def test_generate_small_code_format(self):
        t = Tenant.objects.create(name="مكتب", code="BIG042")
        self.assertEqual(generate_small_office_code(t), "BIG042-SML001")


class LoginTests(APITestCase):
    def setUp(self):
        self.big = create_big_office(name="مكتب دمشق", username="damascus", password="secret123")

    def login(self, **extra):
        return self.client.post(
            reverse("auth-login"),
            {"username": "damascus", "password": "secret123", **extra},
            format="json",
        )

    def test_login_returns_role_claims_and_user(self):
        res = self.login()
        self.assertEqual(res.status_code, 200)
        token = AccessToken(res.data["access"])
        self.assertEqual(token["role"], "big_office")
        self.assertEqual(token["tenant_id"], self.big.tenant_id)
        self.assertEqual(res.data["user"]["role"], "big_office")
        self.assertEqual(res.data["user"]["office_code"], self.big.tenant.code)

    def test_wrong_password_rejected(self):
        res = self.client.post(
            reverse("auth-login"),
            {"username": "damascus", "password": "wrong"},
            format="json",
        )
        self.assertEqual(res.status_code, 401)

    def test_blocked_user_cannot_login(self):
        self.big.is_blocked = True
        self.big.save(update_fields=["is_blocked"])
        self.assertEqual(self.login().status_code, 401)

    def test_inactive_tenant_cannot_login(self):
        self.big.tenant.is_active = False
        self.big.tenant.save(update_fields=["is_active"])
        self.assertEqual(self.login().status_code, 401)

    def test_blocked_enforced_on_requests_even_with_valid_token(self):
        token = self.login().data["access"]
        self.big.is_blocked = True
        self.big.save(update_fields=["is_blocked"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, 401)

    def test_remember_me_extends_refresh(self):
        import datetime

        from rest_framework_simplejwt.tokens import RefreshToken

        short = RefreshToken(self.login().data["refresh"])
        long = RefreshToken(self.login(remember=True).data["refresh"])
        delta = datetime.datetime.fromtimestamp(long["exp"]) - datetime.datetime.fromtimestamp(
            short["exp"]
        )
        self.assertGreater(delta.days, 20)  # 30 يوماً مقابل يوم واحد

    def test_refresh_endpoint(self):
        refresh = self.login().data["refresh"]
        res = self.client.post(reverse("auth-refresh"), {"refresh": refresh}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 401)


class PasswordTests(APITestCase):
    def setUp(self):
        self.big = create_big_office(name="دمشق", username="big1", password="secret123")
        self.small = create_small_office(
            tenant=self.big.tenant, name="حلب", username="small1", password="secret123"
        )
        self.other_big = create_big_office(name="آخر", username="big2", password="secret123")
        self.other_small = create_small_office(
            tenant=self.other_big.tenant, name="غريب", username="small2", password="secret123"
        )
        self.admin = User.objects.create_user(
            username="admin1", password="secret123", role=User.Role.ADMIN
        )

    def auth(self, username):
        res = self.client.post(
            reverse("auth-login"),
            {"username": username, "password": "secret123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_change_own_password(self):
        self.auth("small1")
        res = self.client.post(
            reverse("auth-change-password"),
            {"current_password": "secret123", "new_password": "newpass456"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.small.refresh_from_db()
        self.assertTrue(self.small.check_password("newpass456"))

    def test_change_password_wrong_current_rejected(self):
        self.auth("small1")
        res = self.client.post(
            reverse("auth-change-password"),
            {"current_password": "wrong", "new_password": "newpass456"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_big_resets_own_small(self):
        self.auth("big1")
        res = self.client.post(
            reverse("auth-reset-password"),
            {"user_id": self.small.pk, "new_password": "resetpass789"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.small.refresh_from_db()
        self.assertTrue(self.small.check_password("resetpass789"))

    def test_big_cannot_reset_foreign_small(self):
        """عزل صارم: الكبير لا يستعيد لمكتب صغير تابع لمستأجر آخر."""
        self.auth("big1")
        res = self.client.post(
            reverse("auth-reset-password"),
            {"user_id": self.other_small.pk, "new_password": "resetpass789"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_resets_big_only(self):
        self.auth("admin1")
        ok = self.client.post(
            reverse("auth-reset-password"),
            {"user_id": self.big.pk, "new_password": "resetpass789"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        # الأدمن لا علاقة له بالمكاتب الصغيرة
        denied = self.client.post(
            reverse("auth-reset-password"),
            {"user_id": self.small.pk, "new_password": "resetpass789"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_small_cannot_reset_anyone(self):
        self.auth("small1")
        res = self.client.post(
            reverse("auth-reset-password"),
            {"user_id": self.big.pk, "new_password": "resetpass789"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)


class AvatarTests(APITestCase):
    """صورة البروفايل: تحديث عبر PATCH /me/ وتظهر في بيانات الجلسة."""

    def setUp(self):
        self.user = create_big_office(
            name="مكتب دمشق", username="damascus", password="secret12345"
        )
        res = self.client.post(
            reverse("auth-login"),
            {"username": "damascus", "password": "secret12345"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_patch_avatar_and_read_back(self):
        data_url = "data:image/jpeg;base64,AAAA"
        res = self.client.patch(reverse("auth-me"), {"avatar": data_url}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["avatar"], data_url)
        self.assertEqual(self.client.get(reverse("auth-me")).data["avatar"], data_url)
        # الإزالة
        res = self.client.patch(reverse("auth-me"), {"avatar": ""}, format="json")
        self.assertEqual(res.data["avatar"], "")

    def test_invalid_or_huge_avatar_rejected(self):
        res = self.client.patch(reverse("auth-me"), {"avatar": "http://x/img.png"}, format="json")
        self.assertEqual(res.status_code, 400)
        huge = "data:image/png;base64," + "A" * 500_000
        res = self.client.patch(reverse("auth-me"), {"avatar": huge}, format="json")
        self.assertEqual(res.status_code, 400)


class RegisterTests(APITestCase):
    payload = {
        "office_name": "مكتب جديد",
        "username": "newoffice",
        "phone": "+90500000000",
        "password": "secret123",
        "password_confirm": "secret123",
        "accept_terms": True,
    }

    def test_register_disabled_by_default(self):
        res = self.client.post(reverse("auth-register"), self.payload, format="json")
        self.assertEqual(res.status_code, 403)

    def test_register_when_enabled_creates_inactive_tenant(self):
        s = PlatformSettings.load()
        s.self_registration_enabled = True
        s.save()
        res = self.client.post(reverse("auth-register"), self.payload, format="json")
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(username="newoffice")
        self.assertEqual(user.role, User.Role.BIG_OFFICE)
        self.assertFalse(user.tenant.is_active)  # بانتظار تفعيل الأدمن
        # لا يستطيع الدخول قبل التفعيل
        login = self.client.post(
            reverse("auth-login"),
            {"username": "newoffice", "password": "secret123"},
            format="json",
        )
        self.assertEqual(login.status_code, 401)

    def test_register_requires_terms(self):
        s = PlatformSettings.load()
        s.self_registration_enabled = True
        s.save()
        res = self.client.post(
            reverse("auth-register"),
            {**self.payload, "accept_terms": False},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_register_password_mismatch(self):
        s = PlatformSettings.load()
        s.self_registration_enabled = True
        s.save()
        res = self.client.post(
            reverse("auth-register"),
            {**self.payload, "password_confirm": "different"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
