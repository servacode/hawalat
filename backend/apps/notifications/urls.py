from django.urls import path

from .views import (
    MarkReadView,
    NotificationsView,
    OfficeBroadcastView,
    SmallBroadcastsView,
)

urlpatterns = [
    path("notifications/", NotificationsView.as_view(), name="notifications"),
    path("notifications/read-all/", MarkReadView.as_view(), name="notifications-read-all"),
    path("notifications/<int:pk>/read/", MarkReadView.as_view(), name="notification-read"),
    path("office/alerts/", OfficeBroadcastView.as_view(), name="office-alerts"),
    path("small/alerts/", SmallBroadcastsView.as_view(), name="small-alerts"),
]
