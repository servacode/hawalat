"""
حوالات — المستخدم المخصص والأدوار (RBAC — ق4)
================================================
دخول موحّد، والدور يحدد الواجهة والصلاحيات:
- admin: صاحب المنصة — إداري بحت، بلا مستأجر وبلا أي وصول مالي.
- big_office: المكتب الكبير — مستخدم واحد لكل مستأجر.
- small_office: المكتب الصغير — مستخدم واحد تابع لمستأجر.
"""

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import Tenant


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "أدمن المنصة"
        BIG_OFFICE = "big_office", "مكتب كبير"
        SMALL_OFFICE = "small_office", "مكتب صغير"

    role = models.CharField("الدور", max_length=20, choices=Role.choices)
    tenant = models.ForeignKey(
        Tenant,
        verbose_name="المستأجر",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
    )
    # كود المكتب الصغير الفريد، مرتبط بكود مكتبه الكبير (مثل BIG042-SML007)
    office_code = models.CharField("كود المكتب", max_length=32, blank=True)
    phone = models.CharField("رقم هاتف واتساب", max_length=32, blank=True)
    whatsapp_group_name = models.CharField("اسم مجموعة الواتساب", max_length=150, blank=True)
    whatsapp_group_link = models.URLField("رابط مجموعة الواتساب", blank=True)
    # معرّف المحادثة للبوت (اختياري — يُستخدم فقط عند تفعيل وضع البوت)
    whatsapp_chat_id = models.CharField("معرّف مجموعة البوت", max_length=100, blank=True)
    is_blocked = models.BooleanField("محظور", default=False)

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def clean(self):
        super().clean()
        # الأدمن بلا مستأجر؛ المكاتب (كبير/صغير) يجب أن تتبع مستأجراً
        if self.role == self.Role.ADMIN and self.tenant_id is not None:
            raise ValidationError("الأدمن إداري بحت — لا يتبع أي مستأجر.")
        if self.role in (self.Role.BIG_OFFICE, self.Role.SMALL_OFFICE) and self.tenant_id is None:
            raise ValidationError("مستخدم المكتب يجب أن يتبع مستأجراً.")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
