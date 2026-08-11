from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticación y Registro
    path('registro/', views.registro, name='registro'),
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    
    # Verificación de Email
    path('verificar-email/<str:token>/', views.verificar_email, name='verificar_email'),

    # Perfil y Configuración
    path('perfil/', views.perfil, name='perfil'),
    path('onboarding/completar/', views.completar_onboarding, name='completar_onboarding'),

    # Recuperación de Contraseña
    path('olvide-contrasena/', views.solicitar_recuperacion, name='solicitar_recuperacion'),
    path('restablecer-contrasena/<str:token>/', views.restablecer_contrasena, name='restablecer_contrasena'),

    # Gestión de Sesiones
    path('cerrar-sesiones-otros-dispositivos/', views.cerrar_sesiones_otros_dispositivos, name='cerrar_sesiones_otros_dispositivos'),
]