from django.db import connection
from django.http import JsonResponse


def health(request):
    """نقطة فحص الصحة — تتأكد أن الخدمة وقاعدة البيانات تعملان."""
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:  # pragma: no cover - يظهر فقط عند تعطل القاعدة
        db_ok = False
    status = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "degraded", "db": db_ok}, status=status)
