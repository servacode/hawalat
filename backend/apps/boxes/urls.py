from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CreditLimitViewSet,
    ReconciliationPdfView,
    ReconciliationHistoryView,
    CurrencyViewSet,
    IntermediaryBoxViewSet,
    MemberStatementView,
    MyBalancesView,
    ReconciliationView,
    ReverseEntryView,
    MemberPaymentView,
    ShopCashView,
    SmallCurrenciesView,
    SmallStatementView,
)

router = DefaultRouter()
router.register("currencies", CurrencyViewSet, basename="currencies")
router.register("boxes", IntermediaryBoxViewSet, basename="boxes")
router.register("credit-limits", CreditLimitViewSet, basename="credit-limits")

urlpatterns = [
    path("office/", include(router.urls)),
    path("office/shop-cash/", ShopCashView.as_view(), name="shop-cash"),
    path("office/shop-cash/payments/", MemberPaymentView.as_view(), name="shop-cash-payment"),
    path(
        "office/entries/<int:entry_id>/reverse/", ReverseEntryView.as_view(), name="reverse-entry"
    ),
    path("small/balances/", MyBalancesView.as_view(), name="my-balances"),
    path("small/currencies/", SmallCurrenciesView.as_view(), name="small-currencies"),
    path("small/statement/", SmallStatementView.as_view(), name="small-statement"),
    path("small/reconciliation/", ReconciliationView.as_view(), name="small-reconciliation"),
    path(
        "small/reconciliations/",
        ReconciliationHistoryView.as_view(),
        name="small-reconciliations",
    ),
    path(
        "small/reconciliations/<int:rec_id>/pdf/",
        ReconciliationPdfView.as_view(),
        name="small-reconciliation-pdf",
    ),
    path(
        "office/members/<int:user_id>/statement/",
        MemberStatementView.as_view(),
        name="member-statement",
    ),
    path(
        "office/members/<int:user_id>/reconciliation/",
        ReconciliationView.as_view(),
        name="member-reconciliation",
    ),
    path(
        "office/members/<int:user_id>/reconciliations/",
        ReconciliationHistoryView.as_view(),
        name="member-reconciliations",
    ),
    path(
        "office/members/<int:user_id>/reconciliations/<int:rec_id>/pdf/",
        ReconciliationPdfView.as_view(),
        name="member-reconciliation-pdf",
    ),
]
