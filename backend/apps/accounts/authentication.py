"""حوالات — مصادقة JWT مع فرض الحظر وإيقاف المستأجر على كل طلب."""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class BlockAwareJWTAuthentication(JWTAuthentication):
    """يرفض أي طلب من مستخدم محظور أو مستأجر موقوف حتى لو كان التوكن صالحاً."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if getattr(user, "is_blocked", False):
            raise AuthenticationFailed("هذا الحساب محظور — تواصل مع مكتبك.")
        tenant = getattr(user, "tenant", None)
        if tenant is not None and not tenant.is_active:
            raise AuthenticationFailed("هذا المكتب موقوف حالياً.")
        return user
