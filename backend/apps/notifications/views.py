"""حوالات — نقاط الإشعارات والتنبيهات."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.core.permissions import IsBigOffice, IsSmallOffice

from .models import Notification, OfficeBroadcast
from .services import notify, unread_count


def _serialize(n: Notification):
    return {
        "id": n.id,
        "ntype": n.ntype,
        "title": n.title,
        "body": n.body,
        "entity": n.entity,
        "entity_id": n.entity_id,
        "is_read": n.is_read,
        "at": n.created_at,
    }


class NotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user)[:50]
        return Response(
            {"unread": unread_count(request.user), "items": [_serialize(n) for n in qs]}
        )


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        qs = Notification.objects.filter(recipient=request.user, is_read=False)
        if pk is not None:
            qs = qs.filter(pk=pk)
        qs.update(is_read=True)
        return Response({"unread": unread_count(request.user)})


class OfficeBroadcastView(APIView):
    """بث الكبير → كل مكاتبه الصغيرة (الجزء 16)."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request):
        items = OfficeBroadcast.objects.all()[:50]
        return Response(
            [
                {"id": b.id, "title": b.title, "message": b.message, "at": b.created_at}
                for b in items
            ]
        )

    def post(self, request):
        title = (request.data.get("title") or "").strip()
        message = (request.data.get("message") or "").strip()
        if not title or not message:
            return Response({"detail": "العنوان والنص مطلوبان."}, status=400)
        b = OfficeBroadcast.objects.create(
            tenant=request.user.tenant,
            title=title,
            message=message,
            created_by=request.user,
        )
        recipients = User.objects.filter(
            tenant=request.user.tenant, role=User.Role.SMALL_OFFICE, is_blocked=False
        )
        for r in recipients:
            notify(
                r,
                Notification.Type.BROADCAST,
                f"📢 {title}",
                message,
                entity="office_broadcast",
                entity_id=b.id,
            )
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor=request.user,
            action="office_broadcast",
            entity="broadcast",
            entity_id=str(b.id),
        )
        return Response({"id": b.id}, status=status.HTTP_201_CREATED)


class SmallBroadcastsView(APIView):
    """الصغير يشاهد تنبيهات مكتبه الكبير (قسم التنبيهات)."""

    permission_classes = [IsAuthenticated, IsSmallOffice]

    def get(self, request):
        items = OfficeBroadcast.objects.all()[:50]
        return Response(
            [
                {"id": b.id, "title": b.title, "message": b.message, "at": b.created_at}
                for b in items
            ]
        )
