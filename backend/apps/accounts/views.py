"""حوالات — نقاط المصادقة والهوية."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.models import AuditLog, PlatformSettings

from .models import User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    MeSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
)
from .services import create_big_office

__all__ = ["LoginView", "TokenRefreshView"]


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_scope = "login"


class LogoutView(APIView):
    """خروج آمن: يُبطل refresh نهائياً (blacklist) — التوكن المسروق يموت معه."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        token = request.data.get("refresh")
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass  # منتهٍ/مبطَل مسبقاً — الخروج يمضي
        return Response({"detail": "تم تسجيل الخروج."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    MAX_AVATAR_CHARS = 400_000  # ~300KB مشفّرة — تكفي لصورة 256px مضغوطة

    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        """تحديث الملف الشخصي: صورة البروفايل و/أو البريد (يُعتمد عليه لاستعادة كلمة المرور)."""
        fields = []
        if "avatar" in request.data:
            avatar = request.data.get("avatar") or ""
            if avatar and not avatar.startswith("data:image/"):
                return Response({"avatar": "صيغة الصورة غير صالحة."}, status=400)
            if len(avatar) > self.MAX_AVATAR_CHARS:
                return Response({"avatar": "الصورة كبيرة جداً."}, status=400)
            request.user.avatar = avatar
            fields.append("avatar")
        if "email" in request.data:
            email = (request.data.get("email") or "").strip()
            if email:
                try:
                    validate_email(email)
                except DjangoValidationError:
                    return Response({"email": "صيغة البريد غير صالحة."}, status=400)
                if User.objects.exclude(pk=request.user.pk).filter(email__iexact=email).exists():
                    return Response({"email": "البريد الإلكتروني مستخدم مسبقاً."}, status=400)
            request.user.email = email
            fields.append("email")
        if not fields:
            return Response({"detail": "لا شيء لتحديثه."}, status=400)
        request.user.save(update_fields=fields)
        return Response(MeSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        AuditLog.objects.create(
            tenant=request.user.tenant,
            actor=request.user,
            action="change_password",
            entity="user",
            entity_id=str(request.user.pk),
        )
        return Response({"detail": "تم تغيير كلمة المرور."})


class ResetPasswordView(APIView):
    """استعادة هرمية (الجزء 10): الكبير لمستخدمي مستأجره، والأدمن لمستخدمي الكبار."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = User.objects.filter(pk=serializer.validated_data["user_id"]).first()

        allowed = False
        if target is not None:
            if request.user.role == User.Role.ADMIN:
                # الأدمن يستعيد لمستخدمي المكاتب الكبيرة فقط (لا علاقة له بالصغار)
                allowed = target.role == User.Role.BIG_OFFICE
            elif request.user.role == User.Role.BIG_OFFICE:
                # الكبير يستعيد لمستخدمي مستأجره (الصغار) فقط — عزل صارم
                allowed = (
                    target.role == User.Role.SMALL_OFFICE
                    and target.tenant_id == request.user.tenant_id
                )

        if not allowed:
            return Response(
                {"detail": "غير مصرّح بإعادة تعيين كلمة مرور هذا المستخدم."},
                status=status.HTTP_403_FORBIDDEN,
            )

        target.set_password(serializer.validated_data["new_password"])
        target.save(update_fields=["password"])
        AuditLog.objects.create(
            tenant=target.tenant,
            actor=request.user,
            action="reset_password",
            entity="user",
            entity_id=str(target.pk),
        )
        return Response({"detail": "تمت إعادة تعيين كلمة المرور."})


class RegisterView(APIView):
    """تسجيل ذاتي لمكتب كبير — خلف مفتاح الأدمن (معطّل افتراضياً)."""

    permission_classes = [AllowAny]
    throttle_scope = "register"

    @transaction.atomic
    def post(self, request):
        if not PlatformSettings.load().self_registration_enabled:
            return Response(
                {"detail": "التسجيل الذاتي معطّل حالياً — تواصل مع إدارة المنصة."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = create_big_office(
            name=data["office_name"],
            username=data["username"],
            password=data["password"],
            phone=data["phone"],
            email=data["email"],
        )
        # يُنشأ موقوفاً بانتظار تفعيل الأدمن (الدفع اليدوي ثم التفعيل — الجزء 18)
        user.tenant.is_active = False
        user.tenant.save(update_fields=["is_active"])
        AuditLog.objects.create(
            tenant=user.tenant,
            actor=None,
            action="self_register",
            entity="tenant",
            entity_id=str(user.tenant_id),
        )
        return Response(
            {"detail": "تم استلام طلب التسجيل — بانتظار تفعيل إدارة المنصة."},
            status=status.HTTP_201_CREATED,
        )
