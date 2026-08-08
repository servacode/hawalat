"""حوالات — نقاط الواتساب: ربط الرقم (كبير) + الحالة والإرسال (الدوران)."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.models import AuditLog, PlatformSettings
from apps.core.permissions import IsBigOffice

from . import waha
from .models import WhatsAppMessage
from .services import bot_status, get_settings, queue_message


class WhatsAppLinkView(APIView):
    """
    ربط رقم المكتب الكبير (ملاحظة 44):
    GET حالة الربط (+QR إن كان بانتظار المسح) · POST بدء الربط · DELETE فكّه.
    """

    permission_classes = [IsAuthenticated, IsBigOffice]

    def _state(self, request):
        s = get_settings(request.user.tenant)
        if not PlatformSettings.load().waha_url:
            return {
                "configured": False,
                "status": "NOT_CONFIGURED",
                "number": "",
                "qr": None,
            }
        try:
            data = waha.session_status(request.user.tenant)
        except waha.WahaError as exc:
            return {
                "configured": True,
                "status": "OFFLINE",
                "number": s.linked_number,
                "qr": None,
                "detail": str(exc),
            }
        st = data.get("status", "NOT_STARTED")
        qr = None
        if st == "WORKING":
            me = data.get("me") or {}
            number = str(me.get("id") or "").split("@")[0]
            if number and s.linked_number != number:
                s.linked_number = number
                s.save(update_fields=["linked_number"])
        elif st == "SCAN_QR_CODE":
            try:
                qr = waha.qr_image(request.user.tenant)
            except waha.WahaError:
                qr = None
        return {
            "configured": True,
            "status": st,
            "number": s.linked_number if st == "WORKING" else "",
            "qr": qr,
        }

    def get(self, request):
        return Response(self._state(request))

    def post(self, request):
        try:
            waha.start_session(request.user.tenant)
        except waha.WahaError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor=request.user,
            action="whatsapp_link_start",
            entity="whatsapp_settings",
            entity_id=str(request.user.tenant.pk),
        )
        return Response(self._state(request))

    def delete(self, request):
        s = get_settings(request.user.tenant)
        try:
            waha.logout(request.user.tenant)
        except waha.WahaError:
            pass  # فك الربط محلياً حتى لو الخادم غير متاح
        s.linked_number = ""
        s.save(update_fields=["linked_number"])
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor=request.user,
            action="whatsapp_unlink",
            entity="whatsapp_settings",
            entity_id=str(s.pk),
        )
        return Response({"detail": "فُكّ الربط."})


class WhatsAppSettingsView(APIView):
    """ملخّص حالة الواتساب لشاشة الإعدادات — المكتب الكبير حصراً."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request):
        s = get_settings(request.user.tenant)
        return Response(
            {
                "waha_configured": bool(PlatformSettings.load().waha_url),
                "linked_number": s.linked_number,
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
                {"detail": "رقم الواتساب غير مربوط أو لا وجهة للعضو — استخدم الرابط اليدوي."},
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
