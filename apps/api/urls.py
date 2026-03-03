from django.urls import path

from apps.api.views import N8NWebhookView

app_name = "api"

urlpatterns = [
    path("webhook/n8n/", N8NWebhookView.as_view(), name="n8n_webhook"),
]
