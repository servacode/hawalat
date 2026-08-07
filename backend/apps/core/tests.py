"""
حوالات — اختبارات النواة المركزية
====================================
تفحص القواعد الصارمة: العزل (ق2)، توازن القيود ولا-حذف (ق3)، والأدوار (ق4).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Account, JournalEntry, Tenant
from .services import post_entry, reverse_entry
from .tenancy import tenant_context

User = get_user_model()

D = Decimal


def make_tenant(code):
    return Tenant.objects.create(name=f"مكتب {code}", code=code)


def make_account(tenant, name, kind, currency="USD"):
    return Account.all_objects.create(tenant=tenant, name=name, kind=kind, currency=currency)


class HealthEndpointTests(TestCase):
    def test_health_ok(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class TenantIsolationTests(TestCase):
    """ق2: لا استعلام يرى بيانات مستأجر آخر."""

    def setUp(self):
        self.t1 = make_tenant("BIG001")
        self.t2 = make_tenant("BIG002")
        make_account(self.t1, "صندوق الوعد", Account.Kind.INTERMEDIARY_BOX)
        make_account(self.t2, "صندوق الفجر", Account.Kind.INTERMEDIARY_BOX)

    def test_context_filters_queryset(self):
        with tenant_context(self.t1):
            names = list(Account.objects.values_list("name", flat=True))
        self.assertEqual(names, ["صندوق الوعد"])

        with tenant_context(self.t2):
            names = list(Account.objects.values_list("name", flat=True))
        self.assertEqual(names, ["صندوق الفجر"])

    def test_no_context_returns_all_for_admin_use(self):
        self.assertEqual(Account.objects.count(), 2)

    def test_auto_assign_tenant_from_context(self):
        with tenant_context(self.t1):
            acc = Account(name="صندوق المحل", kind=Account.Kind.SHOP_CASH, currency="USD")
            acc.save()
        self.assertEqual(acc.tenant, self.t1)


class LedgerEngineTests(TestCase):
    """ق3: القيد المزدوج متوازن دائماً، Decimal حصراً، لا حذف."""

    def setUp(self):
        self.t = make_tenant("BIG010")
        self.small = make_account(self.t, "مكتب حلب", Account.Kind.SMALL_OFFICE)
        self.box = make_account(self.t, "الوعد", Account.Kind.INTERMEDIARY_BOX)
        self.profit = make_account(self.t, "أرباح", Account.Kind.FEES_PROFIT)

    def _post_scene2_entry(self):
        """مثال الدورة §4-أ: مبلغ 1000، رأس مال 10، مستحقة 15 → ربح 5.

        القيد القياسي: مدين الصغير 1015 / دائن الصندوق 1010 / دائن الربح 5.
        """
        return post_entry(
            tenant=self.t,
            entry_type=JournalEntry.EntryType.TRANSACTION,
            memo="قبول حوالة HW-1",
            lines=[
                (self.small, D("1015"), D("0")),  # الصغير يصبح عليه 1015
                (self.box, D("0"), D("1010")),  # الصندوق ينقص 1010 (سحبنا منه)
                (self.profit, D("0"), D("5")),  # الربح 5 (دخل دائن)
            ],
        )

    def test_balanced_entry_posts_and_balances_match_ops_doc(self):
        self._post_scene2_entry()
        # الاصطلاح: balance = مدين − دائن
        self.assertEqual(self.small.balance, D("1015"))  # موجب = عليه
        self.assertEqual(self.box.balance, D("-1010"))  # الصندوق نقص (علينا له)
        self.assertEqual(self.profit.balance, D("-5"))  # دخل دائن
        self.assertEqual(self.profit.display_balance, D("5"))  # يُعرض موجباً
        # توازن كلي: مجموع الأرصدة صفر
        total = self.small.balance + self.box.balance + self.profit.balance
        self.assertEqual(total, D("0"))

    def test_deposit_then_transfer_box_decreases_like_story(self):
        """المشهد 5 ثم 2: إيداع 2000 في الوعد ثم تمرير 1010 → الرصيد 990."""
        post_entry(
            tenant=self.t,
            entry_type=JournalEntry.EntryType.SETTLEMENT,
            memo="اعتماد باسم مكتب حلب",
            lines=[(self.box, D("2000"), D("0")), (self.small, D("0"), D("2000"))],
        )
        self.assertEqual(self.box.balance, D("2000"))  # الإيداع زاد الصندوق
        self.assertEqual(self.small.balance, D("-2000"))  # الصغير له (دفع مقدماً)
        self._post_scene2_entry()
        self.assertEqual(self.box.balance, D("990"))  # الحركة أنقصت الصندوق
        self.assertEqual(self.small.balance, D("-985"))  # 1015 عليه − 2000 له

    def test_unbalanced_entry_rejected(self):
        with self.assertRaises(ValidationError):
            post_entry(
                tenant=self.t,
                entry_type=JournalEntry.EntryType.MANUAL,
                lines=[(self.small, D("100"), D("0")), (self.box, D("0"), D("99"))],
            )

    def test_multi_currency_balance_is_per_currency(self):
        box_try = make_account(self.t, "الوعد-تركي", Account.Kind.INTERMEDIARY_BOX, "TRY")
        with self.assertRaises(ValidationError):
            # مدين بالدولار مقابل دائن بالتركي — غير متوازن لكل عملة
            post_entry(
                tenant=self.t,
                entry_type=JournalEntry.EntryType.MANUAL,
                lines=[(self.small, D("100"), D("0")), (box_try, D("0"), D("100"))],
            )

    def test_floats_rejected(self):
        with self.assertRaises(ValidationError):
            post_entry(
                tenant=self.t,
                entry_type=JournalEntry.EntryType.MANUAL,
                lines=[(self.small, 100.0, D("0")), (self.box, D("0"), 100.0)],
            )

    def test_cross_tenant_accounts_rejected(self):
        other = make_tenant("BIG099")
        foreign = make_account(other, "دخيل", Account.Kind.SMALL_OFFICE)
        with self.assertRaises(ValidationError):
            post_entry(
                tenant=self.t,
                entry_type=JournalEntry.EntryType.MANUAL,
                lines=[(self.small, D("10"), D("0")), (foreign, D("0"), D("10"))],
            )

    def test_no_delete_ever(self):
        entry = self._post_scene2_entry()
        with self.assertRaises(ValidationError):
            entry.delete()
        with self.assertRaises(ValidationError):
            entry.lines.first().delete()

    def test_reversal_restores_balances(self):
        entry = self._post_scene2_entry()
        reverse_entry(entry)
        self.assertEqual(self.small.balance, D("0"))
        self.assertEqual(self.box.balance, D("0"))
        self.assertEqual(self.profit.balance, D("0"))
        # الأصل يبقى موجوداً وموسوماً
        entry.refresh_from_db()
        self.assertTrue(hasattr(entry, "reversed_by"))

    def test_double_reversal_rejected(self):
        entry = self._post_scene2_entry()
        reverse_entry(entry)
        with self.assertRaises(ValidationError):
            reverse_entry(entry)


class UserRoleTests(TestCase):
    """ق4: الأدمن بلا مستأجر، والمكاتب تتبع مستأجراً."""

    def setUp(self):
        self.t = make_tenant("BIG020")

    def test_admin_cannot_have_tenant(self):
        u = User(username="admin1", role=User.Role.ADMIN, tenant=self.t)
        with self.assertRaises(ValidationError):
            u.full_clean()

    def test_office_requires_tenant(self):
        u = User(username="office1", role=User.Role.BIG_OFFICE)
        with self.assertRaises(ValidationError):
            u.full_clean()

    def test_valid_users(self):
        User.objects.create_user(username="a", role=User.Role.ADMIN)
        User.objects.create_user(username="b", role=User.Role.BIG_OFFICE, tenant=self.t)
        User.objects.create_user(
            username="s",
            role=User.Role.SMALL_OFFICE,
            tenant=self.t,
            office_code="BIG020-SML001",
        )
        self.assertEqual(User.objects.count(), 3)
