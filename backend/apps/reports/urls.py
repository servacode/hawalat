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
    # تقارير الصغير أُلغيت (ملاحظة التجربة 11): الصغير يدير نفسه من صناديقه وكشوفه
]
