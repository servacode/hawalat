"""حوالات — نقاط الواتساب: الإعدادات (كبير) + الحالة والإرسال (الدوران)."""

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.core.permissions import IsBigOffice

from .models import WhatsAppMessage
from .services import bot_status, get_settings, queue_message


class SettingsSerializer(serializers.Serializer):
    bot_enabled = serializers.BooleanField(required=False)
    gateway_url = serializers.URLField(required=False, allow_blank=True)
    gateway_token = serializers.CharField(required=False, allow_blank=True)


class WhatsAppSettingsView(APIView):
    """إعدادات البوت — المكتب الكبير حصراً (هو من يتحكم بكل شيء)."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request):
        s = get_settings(request.user.tenant)
        return Response(
            {
                "bot_enabled": s.bot_enabled,
                "gateway_url": s.gateway_url,
                "has_token": bool(s.gateway_token),
                "is_ready": s.is_ready,
            }
        )

    def patch(self, request):
        serializer = SettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        s = get_settings(request.user.tenant)
        for field, value in serializer.validated_data.items():
            setattr(s, field, value)
        s.save()
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor=request.user,
            action="update_whatsapp_settings",
            entity="whatsapp_settings",
            entity_id=str(s.pk),
            data={"bot_enabled": s.bot_enabled},
        )
        return Response(
            {
                "bot_enabled": s.bot_enabled,
                "gateway_url": s.gateway_url,
                "has_token": bool(s.gateway_token),
                "is_ready": s.is_ready,
            }
        )


class BotStatusView(APIView):
    """حالة البوت للمستخدم الحالي — تقرّر سلوك زر الإرسال في الواجهة."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(bot_status(request.user))


class SendView(APIView):
    """
    إرسال نص عبر البوت:
    - الصغير: إلى مجموعته هو فقط.
    - الكبير: إلى مجموعة أحد أعضائه (member_id).
    يعيد 409 إن كان الوضع يدوياً (الواجهة تتحول للرابط).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "النص مطلوب."}, status=400)

        if request.user.role == User.Role.SMALL_OFFICE:
            target = request.user
        elif request.user.role == User.Role.BIG_OFFICE:
            target = User.objects.filter(
                pk=request.data.get("member_id"),
                tenant=request.user.tenant,
                role=User.Role.SMALL_OFFICE,
            ).first()
            if target is None:
                return Response({"detail": "العضو غير موجود ضمن مكتبك."}, status=400)
        else:
            return Response(status=403)

        msg = queue_message(to_user=target, text=text)
        if msg is None:
            return Response(
                {"detail": "وضع البوت غير مفعّل/غير مضبوط — استخدم الرابط اليدوي."},
                status=status.HTTP_409_CONFLICT,
            )
        msg.refresh_from_db()
        return Response(
            {"id": msg.pk, "status": msg.status, "error": msg.last_error},
            status=status.HTTP_202_ACCEPTED,
        )


class OutboxView(APIView):
    """سجل رسائل البوت — للكبير (تتبّع/تشخيص)."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request):
        items = WhatsAppMessage.objects.select_related("to_user")[:50]
        return Response(
            [
                {
                    "id": m.pk,
                    "to": m.to_user.first_name or m.to_user.username,
                    "chat_id": m.chat_id,
                    "text": m.text[:80],
                    "status": m.status,
                    "attempts": m.attempts,
                    "error": m.last_error,
                    "at": m.created_at,
                }
                for m in items
            ]
        )
