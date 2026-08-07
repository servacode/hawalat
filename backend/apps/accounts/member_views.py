"""
حوالات — قسم «الحسابات» لدى المكتب الكبير (الجزء 10)
========================================================
فتح/تعديل/حظر مكاتب صغيرة + ملف كل عضو (واتساب، هاتف، كود) — ضمن مستأجره حصراً.
فتح عضو جديد يخضع لحد الباقة (can_create_small_office) مع قاعدة الترحيل.
"""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.admin_panel.services import can_create_small_office
from apps.core.models import AuditLog
from apps.core.permissions import IsBigOffice

from .models import User
from .services import create_small_office


class MemberSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="first_name")

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "username",
            "office_code",
            "phone",
            "whatsapp_group_name",
            "whatsapp_group_link",
            "whatsapp_chat_id",
            "is_blocked",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "office_code", "date_joined", "is_blocked"]


class CreateMemberSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=32, allow_blank=True, default="")
    whatsapp_group_name = serializers.CharField(max_length=150, allow_blank=True, default="")
    whatsapp_group_link = serializers.URLField(allow_blank=True, default="")
    whatsapp_chat_id = serializers.CharField(max_length=100, allow_blank=True, default="")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("اسم المستخدم مستخدم مسبقاً.")
        return value


class MembersViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsBigOffice]

    def _qs(self, request):
        return User.objects.filter(
            tenant=request.user.tenant, role=User.Role.SMALL_OFFICE
        ).order_by("office_code")

    def _audit(self, request, action_name, member):
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor=request.user,
            action=action_name,
            entity="member",
            entity_id=member.office_code or str(member.pk),
        )

    def list(self, request):
        return Response(MemberSerializer(self._qs(request), many=True).data)

    def create(self, request):
        ok, reason = can_create_small_office(request.user.tenant)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)
        serializer = CreateMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = create_small_office(tenant=request.user.tenant, **serializer.validated_data)
        self._audit(request, "create_member", member)
        return Response(MemberSerializer(member).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        member = self._qs(request).filter(pk=pk).first()
        if member is None:
            return Response(status=404)
        serializer = MemberSerializer(member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self._audit(request, "update_member", member)
        return Response(MemberSerializer(member).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        member = self._qs(request).filter(pk=pk).first()
        if member is None:
            return Response(status=404)
        member.is_blocked = True
        member.save(update_fields=["is_blocked"])
        self._audit(request, "block_member", member)
        return Response({"detail": "تم حظر المكتب."})

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        member = self._qs(request).filter(pk=pk).first()
        if member is None:
            return Response(status=404)
        member.is_blocked = False
        member.save(update_fields=["is_blocked"])
        self._audit(request, "unblock_member", member)
        return Response({"detail": "تم فك الحظر."})
