"""إنشاء أدمن المنصة (الدور admin — إداري بحت) من سطر الأوامر."""

import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "ينشئ مستخدم أدمن المنصة (يدير المكاتب الكبيرة والباقات فقط)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--name", default="مدير المنصة")
        parser.add_argument(
            "--password",
            help="اتركه فارغاً ليُطلب تفاعلياً (أكثر أماناً من سطر الأوامر).",
        )

    def handle(self, *args, **options):
        username = options["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError(f"اسم المستخدم «{username}» موجود مسبقاً.")
        password = options.get("password") or getpass.getpass("كلمة المرور: ")
        validate_password(password)
        User.objects.create_user(
            username=username,
            password=password,
            role=User.Role.ADMIN,
            first_name=options["name"],
        )
        self.stdout.write(self.style.SUCCESS(f"✓ أُنشئ أدمن المنصة: {username}"))
