from django.urls import path

from . import views

app_name = "shipping"

urlpatterns = [
    path("codigo-postal/<str:codigo_postal>/", views.codigo_postal, name="codigo_postal"),
    path("cotizar/", views.cotizar, name="cotizar"),
    path("crear/", views.crear, name="crear"),
]
