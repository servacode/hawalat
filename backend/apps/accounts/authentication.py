"""حوالات — مصادقة JWT مع فرض الحظر وإيقاف المستأجر + ضبط سياق العزل.

ملاحظة معمارية مهمة (ق2): مصادقة DRF تحدث بعد Django middleware، لذا ضبط
سياق المستأجر يتم هنا (لحظة التحقق من التوكن) وليس في الـ middleware فقط —
والـ TenantMiddleware يبقى مسؤولاً عن تنظيف السياق في نهاية الطلب.
"""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.tenancy import set_current_tenant


class BlockAwareJWTAuthentication(JWTAuthentication):
    """يرفض المحظور/الموقوف حتى بتوكن صالح، ويضبط سياق العزل للمستأجر."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if getattr(user, "is_blocked", False):
            raise AuthenticationFailed("هذا الحساب محظور — تواصل مع مكتبك.")
        tenant = getattr(user, "tenant", None)
        if tenant is not None and not tenant.is_active:
            raise AuthenticationFailed("هذا المكتب موقوف حالياً.")
        # ضبط سياق العزل (يفلتر TenantManager كل الاستعلامات تلقائياً)
        set_current_tenant(tenant)
        return user
