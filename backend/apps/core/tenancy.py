"""
حوالات — طبقة عزل المستأجرين (Tenancy)
==========================================
كل مكتب كبير = مستأجر (Tenant) معزول تماماً.

الآلية:
- `current_tenant` متغيّر سياق (ContextVar) يضبطه الـ middleware من مستخدم الطلب.
- `TenantManager` يفلتر كل استعلام تلقائياً بالمستأجر الحالي إن كان مضبوطاً.
- `all_objects` مدير غير مفلتر — للاستخدام الإداري/الاختباري الواعي فقط.

قاعدة صارمة (ق2): أي نموذج مالي يرث TenantScopedModel ولا يُستثنى أبداً.
"""

from contextlib import contextmanager
from contextvars import ContextVar

from django.db import models

# المستأجر الحالي لهذا الطلب/السياق (None = سياق غير مقيّد: أدمن/مهام نظام)
_current_tenant: ContextVar = ContextVar("current_tenant", default=None)


def get_current_tenant():
    return _current_tenant.get()


def set_current_tenant(tenant):
    return _current_tenant.set(tenant)


def clear_current_tenant(token=None):
    if token is not None:
        _current_tenant.reset(token)
    else:
        _current_tenant.set(None)


@contextmanager
def tenant_context(tenant):
    """تشغيل كتلة كود ضمن سياق مستأجر محدد (للاختبارات والمهام الخلفية)."""
    token = set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        clear_current_tenant(token)


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantManager(models.Manager):
    """المدير الافتراضي: يفلتر تلقائياً بالمستأجر الحالي إن وُجد في السياق."""

    def get_queryset(self):
        qs = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant is not None:
            qs = qs.filter(tenant=tenant)
        return qs
