"""
حوالات — نقاط لوحة الأدمن
============================
كلها خلف IsPlatformAdmin (ق4). الأدمن إداري بحت: لا يصل لأي رقم مالي —
إحصاءات مجرّدة فقط (عدد مكاتب/حركات)، وإدارة مكاتب وباقات واشتراكات وبث.
"""

from django.contrib.auth.password_validation import validate_password
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.services import create_big_office
from apps.core.models import AuditLog, PlatformSettings, Tenant
from apps.core.permissions import IsBigOffice, IsPlatformAdmin

from .models import AdminBroadcast, Package, Subscription
from .serializers import (
    BigOfficeSerializer,
    BroadcastSerializer,
    CreateBigOfficeSerializer,
    PackageSerializer,
    PlatformSettingsSerializer,
    SubscriptionSerializer,
)


def audit(actor, action_name, entity, entity_id, tenant=None, **data):
    AuditLog.objects.create(
        tenant=tenant,
        actor=actor,
        action=action_name,
        entity=entity,
        entity_id=str(entity_id),
        data=data,
    )


class BigOfficeViewSet(viewsets.ViewSet):
    """إدارة المكاتب الكبيرة: عرض/فتح/تعديل/حظر/تفعيل/استعادة كلمة مرور."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def _annotated(self):
        return Tenant.objects.annotate(
            small_offices_count=Count("users", filter=Q(users__role=User.Role.SMALL_OFFICE))
        ).order_by("-created_at")

    def _enrich(self, tenant):
        owner = tenant.users.filter(role=User.Role.BIG_OFFICE).first()
        tenant.owner_username = owner.username if owner else ""
        tenant.owner_phone = owner.phone if owner else ""
        from .services import get_active_subscription

        sub = get_active_subscription(tenant)
        tenant.active_package = sub.package.name if sub else None
        return tenant

    def list(self, request):
        data = [BigOfficeSerializer(self._enrich(t)).data for t in self._annotated()]
        return Response(data)

    def create(self, request):
        serializer = CreateBigOfficeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validate_password(serializer.validated_data["password"])
        user = create_big_office(**serializer.validated_data)
        audit(request.user, "create_big_office", "tenant", user.tenant_id)
        tenant = self._enrich(self._annotated().get(pk=user.tenant_id))
        return Response(BigOfficeSerializer(tenant).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        tenant = Tenant.objects.filter(pk=pk).first()
        if tenant is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        name = request.data.get("name")
        phone = request.data.get("phone")
        if name:
            tenant.name = name
            tenant.save(update_fields=["name"])
        if phone is not None:
            owner = tenant.users.filter(role=User.Role.BIG_OFFICE).first()
            if owner:
                owner.phone = phone
                owner.save(update_fields=["phone"])
        audit(request.user, "update_big_office", "tenant", tenant.pk)
        return Response(BigOfficeSerializer(self._enrich(self._annotated().get(pk=tenant.pk))).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        tenant = Tenant.objects.filter(pk=pk).first()
        if tenant is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tenant.is_active = False
        tenant.save(update_fields=["is_active"])
        audit(request.user, "block_big_office", "tenant", tenant.pk)
        return Response({"detail": "تم حظر المكتب."})

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        tenant = Tenant.objects.filter(pk=pk).first()
        if tenant is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        tenant.is_active = True
        tenant.save(update_fields=["is_active"])
        audit(request.user, "unblock_big_office", "tenant", tenant.pk)
        return Response({"detail": "تم تفعيل المكتب."})


class PackageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = PackageSerializer
    queryset = Package.objects.all()

    def perform_create(self, serializer):
        pkg = serializer.save()
        audit(self.request.user, "create_package", "package", pkg.pk)

    def perform_update(self, serializer):
        pkg = serializer.save()
        audit(self.request.user, "update_package", "package", pkg.pk)

    def destroy(self, request, *args, **kwargs):
        # لا حذف — تعطيل فقط (اتساقاً مع مبدأ عدم الحذف)
        pkg = self.get_object()
        pkg.is_active = False
        pkg.save(update_fields=["is_active"])
        audit(request.user, "deactivate_package", "package", pkg.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionAdminViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        qs = Subscription.objects.select_related("tenant", "package")
        s = self.request.query_params.get("status")
        return qs.filter(status=s) if s else qs

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        from .services import activate_subscription

        sub = Subscription.objects.filter(pk=pk).first()
        if sub is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if sub.status != Subscription.Status.PENDING:
            return Response(
                {"detail": "هذا الطلب ليس بانتظار التفعيل."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        activate_subscription(sub, admin_user=request.user)
        audit(request.user, "activate_subscription", "subscription", sub.pk, tenant=sub.tenant)
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        sub = Subscription.objects.filter(pk=pk).first()
        if sub is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        sub.status = Subscription.Status.REJECTED
        sub.note = request.data.get("note", "")
        sub.save(update_fields=["status", "note"])
        audit(request.user, "reject_subscription", "subscription", sub.pk, tenant=sub.tenant)
        return Response(SubscriptionSerializer(sub).data)


class PlatformSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.load()).data)

    def patch(self, request):
        obj = PlatformSettings.load()
        serializer = PlatformSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, "update_platform_settings", "settings", 1, **serializer.validated_data)
        return Response(serializer.data)


class AdminStatsView(APIView):
    """إحصاءات غير مالية حصراً (الجزء 18)."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        soon = timezone.now() + timezone.timedelta(days=7)
        return Response(
            {
                "big_offices_total": Tenant.objects.count(),
                "big_offices_active": Tenant.objects.filter(is_active=True).count(),
                "big_offices_blocked": Tenant.objects.filter(is_active=False).count(),
                "small_offices_total": User.objects.filter(role=User.Role.SMALL_OFFICE).count(),
                "pending_subscriptions": Subscription.objects.filter(
                    status=Subscription.Status.PENDING
                ).count(),
                "expiring_soon": Subscription.objects.filter(
                    status=Subscription.Status.ACTIVE, expires_at__lte=soon
                ).count(),
                # عدد الحركات كرقم مجرّد — يُفعَّل مع مرحلة الحركات
                "transactions_total": 0,
            }
        )


class BroadcastViewSet(viewsets.ModelViewSet):
    """بث الأدمن → المكاتب الكبيرة فقط."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = BroadcastSerializer
    queryset = AdminBroadcast.objects.all()
    http_method_names = ["get", "post"]

    def perform_create(self, serializer):
        b = serializer.save(created_by=self.request.user)
        audit(self.request.user, "admin_broadcast", "broadcast", b.pk)


class AuditListView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        logs = AuditLog.objects.select_related("actor")[:100]
        return Response(
            [
                {
                    "id": log.pk,
                    "action": log.action,
                    "entity": log.entity,
                    "entity_id": log.entity_id,
                    "actor": log.actor.username if log.actor else None,
                    "at": log.created_at,
                }
                for log in logs
            ]
        )


# ---------------------------------------------------------------- جانب المكتب الكبير


class OfficeSubscriptionView(APIView):
    """المكتب الكبير: يرى باقاته المتاحة واشتراكاته ويطلب باقة."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request):
        return Response(
            {
                "packages": PackageSerializer(
                    Package.objects.filter(is_active=True), many=True
                ).data,
                "subscriptions": SubscriptionSerializer(
                    Subscription.objects.filter(tenant=request.user.tenant).select_related(
                        "tenant", "package"
                    ),
                    many=True,
                ).data,
                "free_mode": PlatformSettings.load().free_mode,
            }
        )

    def post(self, request):
        package = Package.objects.filter(pk=request.data.get("package"), is_active=True).first()
        if package is None:
            return Response(
                {"detail": "الباقة غير موجودة أو غير متاحة."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Subscription.objects.filter(
            tenant=request.user.tenant, status=Subscription.Status.PENDING
        ).exists():
            return Response(
                {"detail": "لديك طلب سابق بانتظار التفعيل."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sub = Subscription.objects.create(tenant=request.user.tenant, package=package)
        audit(
            request.user, "request_subscription", "subscription", sub.pk, tenant=request.user.tenant
        )
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


class OfficeBroadcastsView(APIView):
    """المكتب الكبير يشاهد تنبيهات الأدمن."""

    permission_classes = [IsAuthenticated, IsBigOffice]

    def get(self, request):
        return Response(BroadcastSerializer(AdminBroadcast.objects.all()[:50], many=True).data)
