from django.urls import path

from .views import BotStatusView, OutboxView, SendView, WhatsAppLinkView, WhatsAppSettingsView

urlpatterns = [
    path("whatsapp/status/", BotStatusView.as_view(), name="wa-status"),
    path("whatsapp/send/", SendView.as_view(), name="wa-send"),
    path("office/whatsapp/", WhatsAppSettingsView.as_view(), name="wa-settings"),
    path("office/whatsapp/link/", WhatsAppLinkView.as_view(), name="wa-link"),
    path("office/whatsapp/outbox/", OutboxView.as_view(), name="wa-outbox"),
]
