from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("mercadopago/retorno/", views.mercadopago_retorno, name="mercadopago_retorno"),
    path("webhook/", views.mercadopago_webhook, name="webhook"),
]
