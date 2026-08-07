"""حوالات — Middleware يضبط المستأجر الحالي من مستخدم الطلب."""

from .tenancy import clear_current_tenant, set_current_tenant


class TenantMiddleware:
    """بعد المصادقة: يضبط سياق المستأجر من user.tenant ويُنظّفه بعد الرد."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            tenant = getattr(user, "tenant", None)
        token = set_current_tenant(tenant)
        try:
            return self.get_response(request)
        finally:
            clear_current_tenant(token)
