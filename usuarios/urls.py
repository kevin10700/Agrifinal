from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('onboarding/completar/', views.completar_onboarding, name='completar_onboarding'),

    # ← str en lugar de uuid
    path('verificar-email/<str:token>/', views.verificar_correo_view, name='verificar_email'),

    path('olvide-contrasena/', views.solicitar_recuperacion, name='solicitar_recuperacion'),
    # ← str en lugar de uuid
    path('restablecer-contrasena/<str:token>/', views.restablecer_contrasena, name='restablecer_contrasena'),

    path('verificar/<str:token>/', views.verificar_correo_view, name='verificar_correo'), 
]
