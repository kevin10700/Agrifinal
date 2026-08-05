from django.urls import path
from . import api

urlpatterns = [
    path('auth/login/', api.login_api),
    path('auth/refresh/', api.refresh_api),
    path('auth/logout/', api.logout_api),
    path('onboarding/completar/', api.completar_onboarding_api),
]
