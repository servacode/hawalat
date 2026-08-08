"""حوالات — Serializers لوحة الأدمن (لا بيانات مالية إطلاقاً)."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.core.models import PlatformSettings, Tenant

from .models import AdminBroadcast, Package, Subscription


class BigOfficeSerializer(serializers.ModelSerializer):
    """عرض مكتب كبير للأدمن — إحصاءات مجرّدة فقط، بلا أي أموال."""

    small_offices_count = serializers.IntegerField(read_only=True)
    owner_username = serializers.CharField(read_only=True)
    owner_phone = serializers.CharField(read_only=True)
    active_package = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "code",
            "is_active",
            "created_at",
            "small_offices_count",
            "owner_username",
            "owner_phone",
            "active_package",
        ]
        read_only_fields = ["id", "code", "created_at"]


class CreateBigOfficeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=32, allow_blank=True, default="")
    email = serializers.EmailField(allow_blank=True, default="")

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("البريد الإلكتروني مستخدم مسبقاً.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("اسم المستخدم مستخدم مسبقاً.")
        return value


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [
            "id",
            "name",
            "max_small_offices",
            "max_transactions",
            "price",
            "currency",
            "duration_days",
            "is_active",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    tenant_code = serializers.CharField(source="tenant.code", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "tenant_name",
            "tenant_code",
            "package",
            "package_name",
            "status",
            "requested_at",
            "activated_at",
            "expires_at",
            "note",
        ]
        read_only_fields = ["status", "requested_at", "activated_at", "expires_at"]


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = ["free_mode", "self_registration_enabled"]


class BroadcastSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminBroadcast
        fields = ["id", "title", "message", "created_at"]
        read_only_fields = ["id", "created_at"]
