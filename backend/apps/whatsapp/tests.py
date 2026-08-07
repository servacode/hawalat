"""حوالات — اختبارات تكامل الواتساب (المرحلة 9)."""

from unittest.mock import patch

from django.urls import reverse as url
from rest_framework.test import APITestCase

from apps.accounts.services import create_big_office, create_small_office
from apps.boxes.models import Currency
from apps.core.tenancy import tenant_context

from .models import WhatsAppMessage
from .services import get_settings

PASSWORD = "secret12345"


class FakeResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


class BaseWaTestCase(APITestCase):
    def setUp(self):
        self.big = create_big_office(name="مكتب دمشق", username="damascus", password=PASSWORD)
        self.tenant = self.big.tenant
        self.small = create_small_office(
            tenant=self.tenant,
            name="مكتب حلب",
            username="aleppo",
            password=PASSWORD,
        )
        self.small.whatsapp_chat_id = "group-123@g.us"
        self.small.save(update_fields=["whatsapp_chat_id"])
        with tenant_context(self.tenant):
            Currency.objects.create(code="USD", name="دولار")

    def auth(self, username):
        res = self.client.post(
            url("auth-login"), {"username": username, "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def enable_bot(self):
        s = get_settings(self.tenant)
        s.bot_enabled = True
        s.gateway_url = "https://gw.example.com/api/send"
        s.gateway_token = "secret-token"
        s.save()


class SettingsTests(BaseWaTestCase):
    def test_default_manual_mode(self):
        self.auth("aleppo")
        res = self.client.get("/api/whatsapp/status/")
        self.assertFalse(res.data["bot_enabled"])

    def test_big_toggles_bot(self):
        self.auth("damascus")
        res = self.client.patch(
            "/api/office/whatsapp/",
            {
                "bot_enabled": True,
                "gateway_url": "https://gw.example.com/send",
                "gateway_token": "t",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_ready"])
        # الصغير يرى الوضع الجديد
        self.auth("aleppo")
        res = self.client.get("/api/whatsapp/status/")
        self.assertTrue(res.data["bot_enabled"])
        self.assertTrue(res.data["chat_configured"])

    def test_small_cannot_touch_settings(self):
        self.auth("aleppo")
        self.assertEqual(self.client.get("/api/office/whatsapp/").status_code, 403)


class SendTests(BaseWaTestCase):
    def test_manual_mode_returns_409(self):
        self.auth("aleppo")
        res = self.client.post("/api/whatsapp/send/", {"text": "مرحبا"}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(WhatsAppMessage.all_objects.count(), 0)

    @patch("apps.whatsapp.gateway.requests.post", return_value=FakeResponse())
    def test_bot_mode_sends_with_auth_header(self, mock_post):
        self.enable_bot()
        self.auth("aleppo")
        res = self.client.post("/api/whatsapp/send/", {"text": "مرحبا"}, format="json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["status"], "sent")
        msg = WhatsAppMessage.all_objects.get()
        self.assertEqual(msg.status, WhatsAppMessage.Status.SENT)
        self.assertEqual(msg.chat_id, "group-123@g.us")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["chatId"], "group-123@g.us")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret-token")

    @patch("apps.whatsapp.gateway.requests.post", return_value=FakeResponse(500, "boom"))
    def test_gateway_failure_marks_failed_after_retries(self, mock_post):
        self.enable_bot()
        self.auth("aleppo")
        res = self.client.post("/api/whatsapp/send/", {"text": "مرحبا"}, format="json")
        self.assertEqual(res.status_code, 202)
        msg = WhatsAppMessage.all_objects.get()
        self.assertEqual(msg.status, WhatsAppMessage.Status.FAILED)
        self.assertGreaterEqual(msg.attempts, 1)
        self.assertIn("500", msg.last_error)

    @patch("apps.whatsapp.gateway.requests.post", return_value=FakeResponse())
    def test_big_sends_to_own_member_only(self, mock_post):
        self.enable_bot()
        other_big = create_big_office(name="آخر", username="ob", password=PASSWORD)
        foreign = create_small_office(
            tenant=other_big.tenant, name="غريب", username="fs", password=PASSWORD
        )
        self.auth("damascus")
        ok = self.client.post(
            "/api/whatsapp/send/",
            {"text": "مطابقة", "member_id": self.small.pk},
            format="json",
        )
        self.assertEqual(ok.status_code, 202)
        denied = self.client.post(
            "/api/whatsapp/send/",
            {"text": "مطابقة", "member_id": foreign.pk},
            format="json",
        )
        self.assertEqual(denied.status_code, 400)

    @patch("apps.whatsapp.gateway.requests.post", return_value=FakeResponse())
    def test_transaction_create_autoqueues_when_bot_on(self, mock_post):
        self.enable_bot()
        self.auth("aleppo")
        res = self.client.post(
            "/api/my/transactions/",
            {
                "sender": "أ",
                "beneficiary": "ب",
                "amount": "100",
                "currency_received": "USD",
                "currency_delivered": "USD",
                "destination": "دمشق",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["whatsapp_bot"]["queued"])
        msg = WhatsAppMessage.all_objects.get()
        self.assertIn(res.data["reference_code"], msg.text)

    def test_transaction_create_manual_when_bot_off(self):
        self.auth("aleppo")
        res = self.client.post(
            "/api/my/transactions/",
            {
                "sender": "أ",
                "beneficiary": "ب",
                "amount": "100",
                "currency_received": "USD",
                "currency_delivered": "USD",
                "destination": "دمشق",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data["whatsapp_bot"]["queued"])
        self.assertEqual(WhatsAppMessage.all_objects.count(), 0)
