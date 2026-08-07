"""
حوالات — خدمة الإشعار المركزية (ق1): كل إشعار يمرّ من هنا حصراً.
تحفظ في القاعدة وتدفع فوراً عبر طبقة القنوات إلى مجموعة المستخدم.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def user_group(user_id: int) -> str:
    return f"user_{user_id}"


def _push(user_id: int, payload: dict):
    layer = get_channel_layer()
    if layer is None:  # بيئة بلا طبقة قنوات (احتياط)
        return
    async_to_sync(layer.group_send)(user_group(user_id), {"type": "push.event", "payload": payload})


def unread_count(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False).count()


def notify(recipient, ntype, title, body="", *, entity="", entity_id="") -> Notification:
    """ينشئ إشعاراً ويدفعه لحظياً (جرس + شارة + حدث تحديث)."""
    n = Notification.objects.create(
        tenant=recipient.tenant,
        recipient=recipient,
        ntype=ntype,
        title=title,
        body=body,
        entity=entity,
        entity_id=str(entity_id),
    )
    _push(
        recipient.id,
        {
            "kind": "notification",
            "id": n.id,
            "ntype": n.ntype,
            "title": n.title,
            "body": n.body,
            "entity": n.entity,
            "entity_id": n.entity_id,
            "at": n.created_at.isoformat(),
            "unread": unread_count(recipient),
        },
    )
    return n


def push_refresh(recipient, scope: str):
    """حدث تحديث بيانات لحظي (بلا إشعار مقروء): scope مثل transactions/balances."""
    _push(recipient.id, {"kind": "refresh", "scope": scope})
