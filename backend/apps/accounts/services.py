"""
حوالات — خدمات الهوية المركزية
=================================
- توليد الأكواد الفريدة (المشهد 6):
  * مكتب كبير:  BIG001, BIG002, ...
  * مكتب صغير:  {كود الكبير}-SML001, ... — الكود يحمل هوية المكتب الكبير (عزل).
"""

import re

from django.db import transaction

from apps.core.models import Tenant

from .models import User

BIG_PREFIX = "BIG"
SMALL_INFIX = "SML"


def generate_big_office_code() -> str:
    """يولّد كود مكتب كبير جديد بصيغة BIGnnn (فريد على مستوى المنصة)."""
    last = 0
    for code in Tenant.objects.values_list("code", flat=True):
        m = re.fullmatch(rf"{BIG_PREFIX}(\d+)", code)
        if m:
            last = max(last, int(m.group(1)))
    return f"{BIG_PREFIX}{last + 1:03d}"


def generate_small_office_code(tenant: Tenant) -> str:
    """يولّد كود مكتب صغير مرتبطاً بكود مكتبه الكبير: BIGnnn-SMLmmm."""
    prefix = f"{tenant.code}-{SMALL_INFIX}"
    last = 0
    codes = User.objects.filter(tenant=tenant, role=User.Role.SMALL_OFFICE).values_list(
        "office_code", flat=True
    )
    for code in codes:
        m = re.fullmatch(rf"{re.escape(prefix)}(\d+)", code or "")
        if m:
            last = max(last, int(m.group(1)))
    return f"{prefix}{last + 1:03d}"


@transaction.atomic
def create_big_office(*, name: str, username: str, password: str, phone: str = "") -> User:
    """ينشئ مستأجراً (مكتباً كبيراً) + مستخدمه الوحيد بكود مولّد."""
    code = generate_big_office_code()
    tenant = Tenant.objects.create(name=name, code=code)
    return User.objects.create_user(
        username=username,
        password=password,
        role=User.Role.BIG_OFFICE,
        tenant=tenant,
        office_code=code,
        phone=phone,
        first_name=name,
    )


@transaction.atomic
def create_small_office(
    *,
    tenant: Tenant,
    name: str,
    username: str,
    password: str,
    phone: str = "",
    whatsapp_group_name: str = "",
    whatsapp_group_link: str = "",
) -> User:
    """ينشئ مكتباً صغيراً تابعاً لمستأجر، بكود مرتبط بكود الكبير."""
    return User.objects.create_user(
        username=username,
        password=password,
        role=User.Role.SMALL_OFFICE,
        tenant=tenant,
        office_code=generate_small_office_code(tenant),
        phone=phone,
        whatsapp_group_name=whatsapp_group_name,
        whatsapp_group_link=whatsapp_group_link,
        first_name=name,
    )
