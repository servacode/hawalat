"""حوالات — Serializers المصادقة والهوية."""

from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User

REMEMBER_ME_REFRESH_LIFETIME = timedelta(days=30)


class LoginSerializer(TokenObtainPairSerializer):
    """دخول موحّد: يضيف الدور والمستأجر للتوكن، ويدعم «تذكّرني» ويمنع المحظورين."""

    remember = serializers.BooleanField(required=False, default=False, write_only=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["tenant_id"] = user.tenant_id
        token["office_code"] = user.office_code
        token["name"] = user.first_name or user.username
        return token

    def validate(self, attrs):
        remember = attrs.pop("remember", False)
        data = super().validate(attrs)

        if self.user.is_blocked:
            raise AuthenticationFailed("هذا الحساب محظور — تواصل مع مكتبك.")
        if self.user.tenant_id and not self.user.tenant.is_active:
            raise AuthenticationFailed("هذا المكتب موقوف حالياً.")

        if remember:
            refresh = self.get_token(self.user)
            refresh.set_exp(lifetime=REMEMBER_ME_REFRESH_LIFETIME)
            data["refresh"] = str(refresh)
            data["access"] = str(refresh.access_token)

        data["user"] = MeSerializer(self.user).data
        return data


class MeSerializer(serializers.ModelSerializer):
    tenant_code = serializers.CharField(source="tenant.code", read_only=True, default=None)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "role",
            "office_code",
            "phone",
            "whatsapp_group_name",
            "whatsapp_group_link",
            "tenant_code",
            "tenant_name",
        ]
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("كلمة المرور الحالية غير صحيحة.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """استعادة هرمية: الكبير لمستخدمي مستأجره، والأدمن لمستخدمي المكاتب الكبيرة."""

    user_id = serializers.IntegerField()
    new_password = serializers.CharField(write_only=True, min_length=8)


class RegisterSerializer(serializers.Serializer):
    """تسجيل ذاتي لمكتب كبير (المشهد 6) — خلف مفتاح الأدمن، ويُنشأ موقوفاً بانتظار التفعيل."""

    office_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    accept_terms = serializers.BooleanField()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "كلمتا المرور غير متطابقتين."})
        if not attrs["accept_terms"]:
            raise serializers.ValidationError(
                {"accept_terms": "يجب الموافقة على الشروط وسياسة الاستخدام."}
            )
        if User.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "اسم المستخدم مستخدم مسبقاً."})
        return attrs
