from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
import logging

logger = logging.getLogger(__name__)


class PanelLoginForm(AuthenticationForm):
    
    #formulario de login
    username = forms.CharField(
        label='Usuario o Correo',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu usuario o correo',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña'
        })
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                logger.warning(f"Intento de login fallido para usuario: {username}")
                raise forms.ValidationError(
                    'Usuario o contraseña incorrectos. Por favor, intenta de nuevo.',
                    code='invalid_login'
                )
            elif self.user_cache.is_superuser:
                # Superusers tienen acceso directo
                logger.info(f"Superuser {username} autenticado para admin_panel")
            else:
                # Verificar si el usuario tiene asignado un rol en el panel administrativo
                try:
                    from .models import UsuarioPanel
                    usuario_panel = UsuarioPanel.objects.select_related('rol').get(usuario=self.user_cache)
                    
                    if not usuario_panel.rol:
                        logger.warning(f"Usuario {username} no tiene rol asignado en UsuarioPanel")
                        raise forms.ValidationError(
                            'No tienes un rol asignado en el panel administrativo. Contacta al administrador.',
                            code='no_role'
                        )
                    elif not usuario_panel.rol.activo:
                        logger.warning(f"Usuario {username} tiene rol inactivo: {usuario_panel.rol.nombre}")
                        raise forms.ValidationError(
                            'Tu rol en el panel administrativo está desactivado. Contacta al administrador.',
                            code='role_inactive'
                        )
                    else:
                        logger.info(f"Usuario {username} tiene rol activo: {usuario_panel.rol.nombre}")
                
                except UsuarioPanel.DoesNotExist:
                    logger.warning(f"Usuario {username} no tiene UsuarioPanel asignado")
                    raise forms.ValidationError(
                        'No tienes permisos para acceder al panel administrativo. Necesitas que te asignen un rol.',
                        code='no_usuario_panel'
                    )
                except Exception as e:
                    logger.error(f"Error al verificar UsuarioPanel para {username}: {str(e)}")
                    raise forms.ValidationError(
                        'Error al verificar permisos. Contacta al administrador.',
                        code='error'
                    )
            
            # Solo confirmar login si pasa todas las validaciones
            if self.user_cache:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data