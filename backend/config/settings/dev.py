"""حوالات — إعدادات التطوير (Development)."""

from .base import *  # noqa: F403

DEBUG = True

# قنوات بلا Redis عند التطوير المحلي السريع (اختبارات/فحوص)
# ملاحظة: مع docker-compose يبقى Redis هو المستخدم عبر REDIS_URL

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# تسريع الاختبارات: hasher خفيف أثناء الاختبار فقط (لا يمسّ الإنتاج)
import os  # noqa: E402
import sys  # noqa: E402

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# طبقة قنوات داخل الذاكرة عند غياب Redis (تطوير محلي/E2E بعملية واحدة)
if not os.environ.get("REDIS_URL"):  # noqa: F405
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    # ومهام Celery تنفَّذ فورياً في نفس العملية
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = False
