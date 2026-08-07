from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MyTransactionsViewSet, OfficeTransactionsViewSet

router = DefaultRouter()
router.register("transactions", OfficeTransactionsViewSet, basename="office-transactions")

my_router = DefaultRouter()
my_router.register("transactions", MyTransactionsViewSet, basename="my-transactions")

urlpatterns = [
    path("office/", include(router.urls)),
    path("my/", include(my_router.urls)),
]
