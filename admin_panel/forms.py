from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm


class PanelLoginForm(AuthenticationForm):
    """
    Formulario de login específico para el Panel Administrativo de AGRIVALE.
    """
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
                raise forms.ValidationError(
                    'Usuario o contraseña incorrectos. Por favor, intenta de nuevo.',
                    code='invalid_login'
                )
            elif not self.user_cache.is_staff:
                raise forms.ValidationError(
                    'No tienes permisos para acceder al panel administrativo.',
                    code='no_permissions'
                )
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data