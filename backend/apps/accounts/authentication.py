"""حوالات — مصادقة JWT مع فرض الحظر على كل طلب."""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class BlockAwareJWTAuthentication(JWTAuthentication):
    """يرفض أي طلب من مستخدم محظور حتى لو كان توكنه صالحاً."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if getattr(user, "is_blocked", False):
            raise AuthenticationFailed("هذا الحساب محظور — تواصل مع مكتبك.")
        return user
