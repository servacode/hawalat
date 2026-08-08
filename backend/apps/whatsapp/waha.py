"""
حوالات — عميل WAHA (ملاحظة 44)
=================================
خادم WAHA واحد تضبطه إدارة المنصة (عنوان + مفتاح)، وجلسة مستقلة لكل
مستأجر باسم ثابت. المكتب الكبير يربط رقمه بمسح QR مرة واحدة، وبعدها
تُرسل المطابقات والحركات مباشرة من رقمه بلا أي رابط.
"""

import base64

import requests


class WahaError(Exception):
    pass


def session_name(tenant) -> str:
    return f"hawalat-{tenant.pk}"


def _config():
    from apps.core.models import PlatformSettings

    p = PlatformSettings.load()
    if not p.waha_url:
        raise WahaError("خادم الواتساب غير مضبوط — يضبطه الأدمن من إعدادات المنصة.")
    return p.waha_url.rstrip("/"), p.waha_key


def _request(method: str, path: str, *, json=None, timeout: int = 15, ok404: bool = False):
    base, key = _config()
    headers = {"X-Api-Key": key} if key else {}
    try:
        response = requests.request(
            method, f"{base}{path}", json=json, headers=headers, timeout=timeout
        )
    except requests.RequestException as exc:
        raise WahaError(f"تعذر الاتصال بخادم الواتساب: {exc}") from exc
    if response.status_code == 404 and ok404:
        return None
    if response.status_code >= 400:
        raise WahaError(f"خادم الواتساب ردّ {response.status_code}: {response.text[:150]}")
    return response


def start_session(tenant):
    """ينشئ جلسة المستأجر (أو يعيد تشغيلها إن كانت موجودة)."""
    name = session_name(tenant)
    try:
        _request("POST", "/api/sessions", json={"name": name, "start": True})
    except WahaError:
        _request("POST", f"/api/sessions/{name}/restart", json={})


def session_status(tenant) -> dict:
    """حالة الجلسة: WORKING/SCAN_QR_CODE/STARTING/STOPPED… أو NOT_STARTED."""
    response = _request("GET", f"/api/sessions/{session_name(tenant)}", ok404=True)
    if response is None:
        return {"status": "NOT_STARTED"}
    return response.json()


def qr_image(tenant) -> str | None:
    """صورة QR الحالية (data URL) — لعرضها في الإعدادات ريثما تُمسح."""
    response = _request("GET", f"/api/{session_name(tenant)}/auth/qr?format=image", ok404=True)
    if response is None:
        return None
    return "data:image/png;base64," + base64.b64encode(response.content).decode()


def logout(tenant):
    """فك الربط: تسجيل خروج الرقم وحذف الجلسة."""
    name = session_name(tenant)
    try:
        _request("POST", f"/api/sessions/{name}/logout", json={})
    finally:
        _request("DELETE", f"/api/sessions/{name}", ok404=True)


def send_text(tenant, chat_id: str, text: str):
    _request(
        "POST",
        "/api/sendText",
        json={"session": session_name(tenant), "chatId": chat_id, "text": text},
        timeout=20,
    )
