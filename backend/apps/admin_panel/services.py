"""
حوالات — منطق الباقات المركزي (Limits & Grandfathering)
==========================================================
القاعدة (المشهد 1):
- الوضع المجاني: كل شيء مفتوح بلا حدود.
- الوضع المدفوع: يلزم اشتراك مفعّل، والحد يسري فقط على ما أُنشئ **بعد** تفعيله —
  ما أُنشئ في الوضع المجاني يبقى ولا يُحتسب (Grandfathering).
"""

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import PlatformSettings

from .models import Subscription


def get_active_subscription(tenant) -> Subscription | None:
    """الاشتراك المفعّل الحالي للمستأجر (غير منتهي المدة)، إن وُجد."""
    now = timezone.now()
    return (
        Subscription.objects.filter(tenant=tenant, status=Subscription.Status.ACTIVE)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .order_by("-activated_at")
        .first()
    )


def can_create_small_office(tenant) -> tuple[bool, str]:
    """هل يستطيع المستأجر فتح مكتب صغير جديد الآن؟ → (مسموح، سبب الرفض)."""
    if PlatformSettings.load().free_mode:
        return True, ""

    sub = get_active_subscription(tenant)
    if sub is None:
        return False, "لا يوجد اشتراك مفعّل — اطلب باقة ليتم تفعيلها من إدارة المنصة."

    # الترحيل: نحتسب فقط المكاتب المُنشأة بعد تفعيل هذا الاشتراك
    counted = User.objects.filter(
        tenant=tenant,
        role=User.Role.SMALL_OFFICE,
        date_joined__gte=sub.activated_at,
    ).count()
    if counted >= sub.package.max_small_offices:
        return False, (
            f"بلغت حد الباقة ({sub.package.max_small_offices} مكتباً بعد التفعيل) — "
            "قم بترقية الباقة."
        )
    return True, ""


def activate_subscription(subscription: Subscription, *, admin_user) -> Subscription:
    """تفعيل الأدمن بعد تأكيد الدفع اليدوي (الجزء 18)."""
    now = timezone.now()
    subscription.status = Subscription.Status.ACTIVE
    subscription.activated_at = now
    subscription.expires_at = now + timezone.timedelta(days=subscription.package.duration_days)
    subscription.activated_by = admin_user
    subscription.save(update_fields=["status", "activated_at", "expires_at", "activated_by"])
    return subscription
