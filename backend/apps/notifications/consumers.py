"""حوالات — مستهلك WebSocket للإشعارات والتحديث اللحظي."""

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .services import user_group


class NotificationsConsumer(AsyncJsonWebsocketConsumer):
    """
    ws://…/ws/notifications/?token=JWT
    المصادقة عبر TokenAuthMiddleware (scope["user"]).
    عند الاتصال: ينضم لمجموعة المستخدم ويستقبل عدّاد غير المقروء.
    """

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group = user_group(user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        from channels.db import database_sync_to_async

        from .services import unread_count

        count = await database_sync_to_async(unread_count)(user)
        await self.send_json({"kind": "hello", "unread": count})

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def push_event(self, event):
        await self.send_json(event["payload"])
