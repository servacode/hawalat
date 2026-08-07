from django.urls import path

from .views import ReportTypesView, ReportView

urlpatterns = [
    path("office/reports/", ReportView.as_view(), {"scope": "office"}, name="office-reports"),
    path(
        "office/reports/types/",
        ReportTypesView.as_view(),
        {"scope": "office"},
        name="office-report-types",
    ),
    path("small/reports/", ReportView.as_view(), {"scope": "small"}, name="small-reports"),
    path(
        "small/reports/types/",
        ReportTypesView.as_view(),
        {"scope": "small"},
        name="small-report-types",
    ),
]
