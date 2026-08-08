from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminStatsView,
    BrandingView,
    AuditListView,
    BigOfficeViewSet,
    BroadcastViewSet,
    OfficeBroadcastsView,
    OfficeSubscriptionView,
    PackageViewSet,
    PlatformSettingsView,
    SubscriptionAdminViewSet,
)

router = DefaultRouter()
router.register("offices", BigOfficeViewSet, basename="admin-offices")
router.register("packages", PackageViewSet, basename="admin-packages")
router.register("subscriptions", SubscriptionAdminViewSet, basename="admin-subscriptions")
router.register("broadcasts", BroadcastViewSet, basename="admin-broadcasts")

urlpatterns = [
    path("admin/", include(router.urls)),
    path("admin/settings/", PlatformSettingsView.as_view(), name="admin-settings"),
    path("platform/branding/", BrandingView.as_view(), name="platform-branding"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("admin/audit/", AuditListView.as_view(), name="admin-audit"),
    path("office/subscription/", OfficeSubscriptionView.as_view(), name="office-subscription"),
    path("office/broadcasts/", OfficeBroadcastsView.as_view(), name="office-broadcasts"),
]
