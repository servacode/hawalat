"""حوالات — اختبارات تكامل الواتساب (المرحلة 9 + ملاحظة 44: ربط الرقم عبر WAHA)."""

from unittest.mock import patch

from django.urls import reverse as url
from rest_framework.test import APITestCase

from apps.accounts.services import create_big_office, create_small_office
from apps.boxes.models import Currency
from apps.core.models import PlatformSettings
from apps.core.tenancy import tenant_context

from .models import WhatsAppMessage
from .services import chat_id_for, get_settings

PASSWORD = "secret12345"


class FakeResponse:
    def __init__(self, status_code=200, text="ok", json_data=None, content=b""):
        self.status_code = status_code
        self.text = text
        self._json = json_data or {}
        self.content = content

    def json(self):
        return self._json


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
            Currency.objects.get(code="USD")

    def auth(self, username):
        res = self.client.post(
            url("auth-login"), {"username": username, "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def link_number(self):
        """يجهّز البيئة: خادم WAHA مضبوط + رقم المكتب مربوط."""
        p = PlatformSettings.load()
        p.waha_url = "https://waha.example.com"
        p.waha_key = "waha-key"
        p.save()
        s = get_settings(self.tenant)
        s.linked_number = "9639900000"
        s.save()


class SettingsTests(BaseWaTestCase):
    def test_default_manual_mode(self):
        self.auth("aleppo")
        res = self.client.get("/api/whatsapp/status/")
        self.assertFalse(res.data["bot_enabled"])

    def test_ready_after_link(self):
        self.link_number()
        self.auth("damascus")
        res = self.client.get("/api/office/whatsapp/")
        self.assertTrue(res.data["is_ready"])
        self.assertEqual(res.data["linked_number"], "9639900000")
        # الصغير يرى الوضع الجديد
        self.auth("aleppo")
        res = self.client.get("/api/whatsapp/status/")
        self.assertTrue(res.data["bot_enabled"])
        self.assertTrue(res.data["chat_configured"])

    def test_small_cannot_touch_settings(self):
        self.auth("aleppo")
        self.assertEqual(self.client.get("/api/office/whatsapp/").status_code, 403)
        self.assertEqual(self.client.get("/api/office/whatsapp/link/").status_code, 403)

    def test_link_view_not_configured(self):
        self.auth("damascus")
        res = self.client.get("/api/office/whatsapp/link/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["configured"])

    @patch("apps.whatsapp.waha.requests.request")
    def test_link_view_scan_qr_flow(self, mock_req):
        """بدء الربط يعيد QR ريثما يُمسح — ثم WORKING يخزّن الرقم."""
        p = PlatformSettings.load()
        p.waha_url = "https://waha.example.com"
        p.save()
        self.auth("damascus")

        # الحالة: بانتظار مسح QR
        def scan_side_effect(method, urlpath, **kwargs):
            if method == "GET" and urlpath.endswith("/auth/qr?format=image"):
                return FakeResponse(content=b"PNGDATA")
            return FakeResponse(json_data={"status": "SCAN_QR_CODE"})

        mock_req.side_effect = scan_side_effect
        res = self.client.post("/api/office/whatsapp/link/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "SCAN_QR_CODE")
        self.assertTrue(str(res.data["qr"]).startswith("data:image/png;base64,"))

        # بعد المسح: WORKING + تخزين الرقم
        mock_req.side_effect = None
        mock_req.return_value = FakeResponse(
            json_data={"status": "WORKING", "me": {"id": "9639900000@c.us", "pushName": "دمشق"}}
        )
        res = self.client.get("/api/office/whatsapp/link/")
        self.assertEqual(res.data["status"], "WORKING")
        self.assertEqual(res.data["number"], "9639900000")
        self.assertEqual(get_settings(self.tenant).linked_number, "9639900000")

    @patch("apps.whatsapp.waha.requests.request", return_value=FakeResponse())
    def test_unlink_clears_number(self, mock_req):
        self.link_number()
        self.auth("damascus")
        res = self.client.delete("/api/office/whatsapp/link/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(get_settings(self.tenant).linked_number, "")

    def test_chat_id_falls_back_to_phone(self):
        """بلا معرّف مجموعة: الإرسال لرقم هاتف العضو مباشرة (ملاحظة 44)."""
        self.small.whatsapp_chat_id = ""
        self.small.phone = "+90 539 593 06 40"
        self.small.save(update_fields=["whatsapp_chat_id", "phone"])
        self.assertEqual(chat_id_for(self.small), "905395930640@c.us")

    @patch("apps.whatsapp.waha.requests.request")
    def test_group_link_resolves_to_group_chat_id(self, mock_req):
        """رابط المجموعة يُستنتج منه معرّفها ويُخزَّن — فتصل الرسالة للمجموعة (ملاحظة 46)."""
        self.link_number()
        self.small.whatsapp_chat_id = ""
        self.small.whatsapp_group_link = "https://chat.whatsapp.com/CmJivBMZcig?s=cl"
        self.small.phone = "+905395930640"
        self.small.save(update_fields=["whatsapp_chat_id", "whatsapp_group_link", "phone"])

        def side_effect(method, urlpath, **kwargs):
            if "groups/join-info" in urlpath:
                self.assertIn("code=CmJivBMZcig", urlpath)
                return FakeResponse(json_data={"id": "120363000111222333@g.us", "subject": "الحسكة"})
            return FakeResponse()

        mock_req.side_effect = side_effect
        self.auth("aleppo")
        res = self.client.post("/api/whatsapp/send/", {"text": "مطابقة"}, format="json")
        self.assertEqual(res.status_code, 202)
        msg = WhatsAppMessage.all_objects.get()
        self.assertEqual(msg.chat_id, "120363000111222333@g.us")
        # المعرّف تخزّن — لا استنتاج مرة أخرى
        self.small.refresh_from_db()
        self.assertEqual(self.small.whatsapp_chat_id, "120363000111222333@g.us")


class SendTests(BaseWaTestCase):
    def test_manual_mode_returns_409(self):
        self.auth("aleppo")
        res = self.client.post("/api/whatsapp/send/", {"text": "مرحبا"}, format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(WhatsAppMessage.all_objects.count(), 0)

    @patch("apps.whatsapp.waha.requests.request", return_value=FakeResponse())
    def test_linked_mode_sends_with_api_key(self, mock_req):
        self.link_number()
        self.auth("aleppo")
        res = self.client.post("/api/whatsapp/send/", {"text": "مرحبا"}, format="json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["status"], "sent")
        msg = WhatsAppMessage.all_objects.get()
        self.assertEqual(msg.status, WhatsAppMessage.Status.SENT)
        self.assertEqual(msg.chat_id, "group-123@g.us")
        args, kwargs = mock_req.call_args
        self.assertEqual(args[0], "POST")
        self.assertTrue(args[1].endswith("/api/sendText"))
        self.assertEqual(kwargs["json"]["chatId"], "group-123@g.us")
        self.assertEqual(kwargs["json"]["session"], f"hawalat-{self.tenant.pk}")
        self.assertEqual(kwargs["headers"]["X-Api-Key"], "waha-key")

    @patch(
        "apps.whatsapp.waha.requests.request",
        return_value=FakeResponse(500, "boom"),
    )
    def test_waha_failure_marks_failed_after_retries(self, mock_req):
        self.link_number()
        self.auth("aleppo")
        res = self.client.post("/api/whatsapp/send/", {"text": "مرحبا"}, format="json")
        self.assertEqual(res.status_code, 202)
        msg = WhatsAppMessage.all_objects.get()
        self.assertEqual(msg.status, WhatsAppMessage.Status.FAILED)
        self.assertGreaterEqual(msg.attempts, 1)
        self.assertIn("500", msg.last_error)

    @patch("apps.whatsapp.waha.requests.request", return_value=FakeResponse())
    def test_big_sends_to_own_member_only(self, mock_req):
        self.link_number()
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

    @patch("apps.whatsapp.waha.requests.request", return_value=FakeResponse())
    def test_transaction_create_autoqueues_when_linked(self, mock_req):
        self.link_number()
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

    def test_transaction_create_manual_when_not_linked(self):
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
