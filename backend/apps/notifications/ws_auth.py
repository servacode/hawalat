"""مصادقة WebSocket بتوكن JWT في الاستعلام (المتصفح لا يرسل ترويسات WS)."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async


@database_sync_to_async
def _get_user(token: str):
    from rest_framework_simplejwt.tokens import AccessToken

    from apps.accounts.models import User

    try:
        access = AccessToken(token)
        user = User.objects.select_related("tenant").get(pk=access["user_id"])
    except Exception:
        return None
    if user.is_blocked or (user.tenant and not user.tenant.is_active):
        return None
    return user


class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        params = parse_qs(scope.get("query_string", b"").decode())
        token = (params.get("token") or [None])[0]
        scope["user"] = await _get_user(token) if token else None
        return await self.app(scope, receive, send)
