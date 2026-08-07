"""حوالات — إعدادات التطوير (Development)."""

from .base import *  # noqa: F403

DEBUG = True

# قنوات بلا Redis عند التطوير المحلي السريع (اختبارات/فحوص)
# ملاحظة: مع docker-compose يبقى Redis هو المستخدم عبر REDIS_URL

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# تسريع الاختبارات: hasher خفيف أثناء الاختبار فقط (لا يمسّ الإنتاج)
import sys  # noqa: E402

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
