"""حوالات — نقطة التقارير الموحّدة (عرض/تصدير) للدورين."""

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .export import to_pdf, to_xlsx
from .services import REPORT_LABELS, REPORTS


class ReportView(APIView):
    """
    GET /api/office/reports/?type=profits&date_from=&date_to=&export=xlsx|pdf
    GET /api/small/reports/?...  (الأنواع المسموحة للصغير فقط، على بياناته)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, scope):
        role = request.user.role
        if scope == "office" and role != User.Role.BIG_OFFICE:
            return Response(status=403)
        if scope == "small" and role != User.Role.SMALL_OFFICE:
            return Response(status=403)

        rtype = request.query_params.get("type", "")
        if rtype not in REPORTS:
            return Response(
                {
                    "detail": "نوع تقرير غير معروف.",
                    "available": [
                        {"type": k, "label": REPORT_LABELS[k]}
                        for k, (_, small_ok) in REPORTS.items()
                        if scope == "office" or small_ok
                    ],
                },
                status=400,
            )
        builder, small_ok = REPORTS[rtype]
        if scope == "small" and not small_ok:
            return Response({"detail": "هذا التقرير غير متاح لك."}, status=403)

        report = builder(
            request.user.tenant,
            request.query_params.get("date_from") or None,
            request.query_params.get("date_to") or None,
            user=request.user if scope == "small" else None,
        )

        fmt = request.query_params.get("export", "json")
        filename = f"hawalat-{rtype}"
        if fmt == "xlsx":
            data = to_xlsx(report)
            resp = HttpResponse(
                data,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            resp["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
            return resp
        if fmt == "pdf":
            data = to_pdf(report)
            resp = HttpResponse(data, content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
            return resp
        return Response(report)


class ReportTypesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, scope):
        role = request.user.role
        if scope == "office" and role != User.Role.BIG_OFFICE:
            return Response(status=403)
        if scope == "small" and role != User.Role.SMALL_OFFICE:
            return Response(status=403)
        return Response(
            [
                {"type": k, "label": REPORT_LABELS[k]}
                for k, (_, small_ok) in REPORTS.items()
                if scope == "office" or small_ok
            ]
        )
