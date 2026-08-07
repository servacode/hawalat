"""حوالات — إعدادات الإنتاج (Production)."""

from .base import *  # noqa: F403

DEBUG = False

# أصول CSRF الموثوقة (مطلوبة خلف بروكسي TLS للوحة الإدارة)
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")  # noqa: F405
    if o.strip()
]

# أمان الإنتاج
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 يوماً — تُرفع لاحقاً بعد الثبات
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# الملفات الساكنة عبر WhiteNoise
MIDDLEWARE.insert(  # noqa: F405
    1, "whitenoise.middleware.WhiteNoiseMiddleware"
)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# كاش Redis (تحديد المعدّل يعمل عبر كل العمليات)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,  # noqa: F405
    }
}
