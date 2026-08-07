"""
حوالات — محوّل البوابة العام (Gateway Adapter)
=================================================
POST بسيط {chatId, text} برأس Authorization — متوافق مع بوابات
واتساب الذاتية الشائعة (مثل WAHA). المزوّد الفعلي يُضبط من شاشة
إعدادات المكتب (عنوان + رمز) بلا أي تغيير كود.
"""

import requests


class GatewayError(Exception):
    pass


def send_via_gateway(*, gateway_url: str, token: str, chat_id: str, text: str, timeout: int = 15):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.post(
            gateway_url,
            json={"chatId": chat_id, "text": text},
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise GatewayError(f"تعذر الاتصال بالبوابة: {exc}") from exc
    if response.status_code >= 400:
        raise GatewayError(f"البوابة ردّت {response.status_code}: {response.text[:150]}")
    return response
