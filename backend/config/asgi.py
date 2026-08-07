"""
حوالات — ASGI entrypoint.

يخدم HTTP عبر Django وWebSockets عبر Channels (يُوسَّع في مرحلة الوقت الحقيقي).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

# يجب تهيئة Django قبل استيراد أي شيء يعتمد على التطبيقات
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # "websocket": ...  ← يُضاف في المرحلة 8 (الوقت الحقيقي)
    }
)
