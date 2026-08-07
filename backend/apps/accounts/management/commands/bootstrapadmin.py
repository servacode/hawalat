"""
إنشاء أدمن المنصة تلقائياً من متغيرات البيئة (للاستضافات بلا Shell).
Idempotent: لا يفعل شيئاً إن كان المستخدم موجوداً أو المتغيرات غائبة.
"""

import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "ينشئ أدمن المنصة من BOOTSTRAP_ADMIN_USERNAME/PASSWORD إن لم يوجد."

    def handle(self, *args, **options):
        username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME")
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
        if not username or not password:
            self.stdout.write("bootstrapadmin: متغيرات غير مضبوطة — تخطٍّ.")
            return
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"bootstrapadmin: «{username}» موجود — تخطٍّ.")
            return
        User.objects.create_user(
            username=username,
            password=password,
            role=User.Role.ADMIN,
            first_name="مدير المنصة",
        )
        self.stdout.write(self.style.SUCCESS(f"✓ أُنشئ أدمن المنصة: {username}"))
