"""حوالات — مهام دورية للاشتراكات (Celery Beat)."""

from celery import shared_task
from django.utils import timezone


@shared_task
def expire_subscriptions():
    """يعلّم الاشتراكات المنتهية المدة ويُشعر أصحابها (يومياً)."""
    from apps.accounts.models import User
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    from .models import Subscription

    now = timezone.now()
    expired = Subscription.objects.filter(status=Subscription.Status.ACTIVE, expires_at__lt=now)
    count = 0
    for sub in expired.select_related("tenant", "package"):
        sub.status = Subscription.Status.EXPIRED
        sub.save(update_fields=["status"])
        owner = User.objects.filter(tenant=sub.tenant, role=User.Role.BIG_OFFICE).first()
        if owner:
            notify(
                owner,
                Notification.Type.SUBSCRIPTION,
                f"انتهت باقتك: {sub.package.name}",
                "جدّد اشتراكك لمواصلة فتح المكاتب والحركات الجديدة.",
                entity="subscription",
                entity_id=sub.pk,
            )
        count += 1
    return count
