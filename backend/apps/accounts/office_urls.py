from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .member_views import MembersViewSet

router = DefaultRouter()
router.register("members", MembersViewSet, basename="members")

urlpatterns = [
    path("office/", include(router.urls)),
]
