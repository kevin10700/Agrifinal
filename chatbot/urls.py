from django.urls import path
from . import views, admin_views

urlpatterns = [
    path("mensaje/", views.chatbot_mensaje, name="chatbot_mensaje"),
    path("admin-chat/", admin_views.chatbot_admin_mensaje, name="chatbot_admin_mensaje"),
    path("admin-chat/panel/", admin_views.chatbot_admin_panel, name="chatbot_admin_panel"),
]