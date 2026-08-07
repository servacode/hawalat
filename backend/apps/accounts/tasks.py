"""حوالات — مهام دورية للمصادقة."""

from celery import shared_task
from django.core.management import call_command


@shared_task
def flush_expired_tokens():
    """تنظيف جدول التوكنات المبطَلة/المنتهية (يومياً)."""
    call_command("flushexpiredtokens")
