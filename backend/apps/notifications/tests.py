"""حوالات — اختبارات الإشعارات والتنبيهات والمستهلك (المرحلة 8)."""

from decimal import Decimal

from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase
from django.urls import reverse as url
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.services import create_big_office, create_small_office
from apps.boxes.models import Currency, IntermediaryBox
from apps.core.tenancy import tenant_context

from .models import Notification

D = Decimal
PASSWORD = "secret12345"


class BaseNotifTestCase(APITestCase):
    def setUp(self):
        self.big = create_big_office(name="مكتب دمشق", username="damascus", password=PASSWORD)
        self.tenant = self.big.tenant
        self.small = create_small_office(
            tenant=self.tenant, name="مكتب حلب", username="aleppo", password=PASSWORD
        )
        with tenant_context(self.tenant):
            usd = Currency.objects.create(code="USD", name="دولار")
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


class TriggerTests(BaseNotifTestCase):
    def _send_txn(self):
        self.auth("aleppo")
        return self.client.post(
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

    def test_new_transaction_notifies_big(self):
        self._send_txn()
        n = Notification.objects.filter(recipient=self.big, ntype=Notification.Type.TXN_NEW)
        self.assertEqual(n.count(), 1)

    def test_approve_notifies_small(self):
        txn = self._send_txn()
        self.auth("damascus")
        self.client.post(
            f"/api/office/transactions/{txn['id']}/approve/",
            {"box": self.box.pk, "fee_cost": "10", "fee_charged": "15"},
            format="json",
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.small, ntype=Notification.Type.TXN_ACCEPTED
            ).exists()
        )

    def test_reject_and_paid_notify_small(self):
        t1 = self._send_txn()
        t2 = self._send_txn()
        self.auth("damascus")
        self.client.post(f"/api/office/transactions/{t1['id']}/reject/")
        self.client.post(
            f"/api/office/transactions/{t2['id']}/approve/",
            {"box": self.box.pk, "fee_cost": "1", "fee_charged": "2"},
            format="json",
        )
        self.client.post(f"/api/office/transactions/{t2['id']}/pay/")
        types = set(
            Notification.objects.filter(recipient=self.small).values_list("ntype", flat=True)
        )
        self.assertIn(Notification.Type.TXN_REJECTED, types)
        self.assertIn(Notification.Type.TXN_PAID, types)

    def test_deposit_notifies_small(self):
        self.auth("damascus")
        self.client.post(
            f"/api/office/boxes/{self.box.pk}/deposit/",
            {"small_user": self.small.pk, "currency": "USD", "amount": "500"},
            format="json",
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.small, ntype=Notification.Type.SETTLEMENT
            ).exists()
        )

    def test_office_broadcast_fans_out(self):
        create_small_office(tenant=self.tenant, name="حمص", username="homs", password=PASSWORD)
        self.auth("damascus")
        res = self.client.post(
            "/api/office/alerts/",
            {"title": "إجازة الجمعة", "message": "المكتب مغلق"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Notification.objects.filter(ntype=Notification.Type.BROADCAST).count(), 2)
        # الصغير يشاهدها في قسم تنبيهاته
        self.auth("aleppo")
        res = self.client.get("/api/small/alerts/")
        self.assertEqual(res.data[0]["title"], "إجازة الجمعة")

    def test_unread_and_read_all(self):
        self._send_txn()
        self.auth("damascus")
        res = self.client.get("/api/notifications/")
        self.assertEqual(res.data["unread"], 1)
        self.assertEqual(res.data["items"][0]["ntype"], "txn_new")
        res = self.client.post("/api/notifications/read-all/")
        self.assertEqual(res.data["unread"], 0)

    def test_notifications_are_private(self):
        self._send_txn()  # إشعار للكبير
        self.auth("aleppo")
        res = self.client.get("/api/notifications/")
        self.assertEqual(res.data["unread"], 0)


class ConsumerTests(TransactionTestCase):
    """اتصال WebSocket بالتوكن واستقبال دفعة لحظية."""

    def setUp(self):
        self.big = create_big_office(name="مكتب", username="ws_big", password=PASSWORD)

    async def _connect(self, token):
        from config.asgi import application

        comm = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
        connected, _ = await comm.connect()
        return comm, connected

    async def test_rejects_without_token(self):
        from config.asgi import application

        comm = WebsocketCommunicator(application, "/ws/notifications/")
        connected, _ = await comm.connect()
        self.assertFalse(connected)

    async def test_connect_hello_and_live_push(self):
        token = str(AccessToken.for_user(self.big))
        comm, connected = await self._connect(token)
        self.assertTrue(connected)
        hello = await comm.receive_json_from()
        self.assertEqual(hello["kind"], "hello")

        # دفعة لحظية عبر notify
        from channels.db import database_sync_to_async

        from .models import Notification
        from .services import notify

        await database_sync_to_async(notify)(
            self.big, Notification.Type.BROADCAST, "اختبار لحظي", "مرحبا"
        )
        msg = await comm.receive_json_from(timeout=5)
        self.assertEqual(msg["kind"], "notification")
        self.assertEqual(msg["title"], "اختبار لحظي")
        self.assertEqual(msg["unread"], 1)
        await comm.disconnect()
