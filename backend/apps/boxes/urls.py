from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CreditLimitViewSet,
    CurrencyViewSet,
    IntermediaryBoxViewSet,
    MyBalancesView,
    ReverseEntryView,
    ShopCashView,
)

router = DefaultRouter()
router.register("currencies", CurrencyViewSet, basename="currencies")
router.register("boxes", IntermediaryBoxViewSet, basename="boxes")
router.register("credit-limits", CreditLimitViewSet, basename="credit-limits")

urlpatterns = [
    path("office/", include(router.urls)),
    path("office/shop-cash/", ShopCashView.as_view(), name="shop-cash"),
    path(
        "office/entries/<int:entry_id>/reverse/", ReverseEntryView.as_view(), name="reverse-entry"
    ),
    path("small/balances/", MyBalancesView.as_view(), name="my-balances"),
]
