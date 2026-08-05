from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario, DireccionEnvio


class RegistroForm(UserCreationForm):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Elige un nombre de usuario"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "ejemplo@correo.com"}),
    )
    nombre = forms.CharField(
        label="Nombre(s)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Tu(s) nombre(s)"}),
    )
    apellido_paterno = forms.CharField(
        label="Apellidos",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. García López"}),
    )
    apellido_materno = forms.CharField(
        label="Apellido materno",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido materno (opcional)"}),
    )
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Crea una contraseña segura"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repite la contraseña"}),
    )

    class Meta:
        model = Usuario
        fields = [
            "username", "email",
            "nombre", "apellido_paterno", "apellido_materno",
            "fecha_nacimiento",
            "password1", "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = """
            <ul class="text-muted small">
                <li>Tu contraseña no puede ser similar a tu información personal.</li>
                <li>Tu contraseña debe contener al menos 8 caracteres.</li>
                <li>Tu contraseña no puede ser una contraseña común.</li>
                <li>Tu contraseña no puede ser completamente numérica.</li>
            </ul>
        """
        self.fields["password2"].help_text = "Ingresa la misma contraseña para verificarla."

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ingresa tu usuario"}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Ingresa tu contraseña"}),
    )


class PerfilForm(forms.ModelForm):
    """Edición de datos personales del usuario."""

    class Meta:
        model = Usuario
        fields = [
            "nombre", "apellido_paterno", "apellido_materno",
            "email",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tu(s) nombre(s)"}),
            "apellido_paterno": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido paterno"}),
            "apellido_materno": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido materno"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "ejemplo@correo.com"}),
        }
        labels = {
            "nombre": "Nombre(s)",
            "apellido_paterno": "Apellido paterno",
            "apellido_materno": "Apellido materno (opcional)",
            "email": "Correo electrónico",
        }


class DireccionEnvioForm(forms.ModelForm):
    """Formulario para agregar o editar una dirección de envío."""

    class Meta:
        model = DireccionEnvio
        fields = [
            "nombre_referencia",
            "calle", "numero_exterior", "numero_interior",
            "colonia", "municipio", "estado", "codigo_postal", "pais", "referencias",
            "telefono_contacto", "es_principal",
        ]
        widgets = {
            "nombre_referencia": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Casa, Oficina"}),
            "calle": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la calle"}),
            "numero_exterior": forms.TextInput(attrs={"class": "form-control", "placeholder": "No. exterior"}),
            "numero_interior": forms.TextInput(attrs={"class": "form-control", "placeholder": "No. interior (opcional)"}),
            "colonia": forms.TextInput(attrs={"class": "form-control", "placeholder": "Colonia"}),
            "municipio": forms.TextInput(attrs={"class": "form-control", "placeholder": "Municipio"}),
            "estado": forms.TextInput(attrs={"class": "form-control", "placeholder": "Estado"}),
            "codigo_postal": forms.TextInput(attrs={"class": "form-control", "placeholder": "Código postal"}),
            "pais": forms.TextInput(attrs={"class": "form-control", "placeholder": "MX"}),
            "referencias": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Ej. Casa con portón verde frente a la iglesia"}),
            "telefono_contacto": forms.TextInput(attrs={"class": "form-control", "placeholder": "Teléfono de contacto"}),
            "es_principal": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "nombre_referencia": "Nombre de referencia",
            "calle": "Calle",
            "numero_exterior": "Número exterior",
            "numero_interior": "Número interior",
            "colonia": "Colonia",
            "municipio": "Municipio",
            "estado": "Estado",
            "codigo_postal": "Código postal",
            "pais": "País",
            "referencias": "Referencias de entrega",
            "telefono_contacto": "Teléfono de contacto",
            "es_principal": "Establecer como dirección principal",
        }


class SolicitarRecuperacionForm(forms.Form):
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Ingresa tu correo registrado",
        }),
    )


class NuevaContrasenaForm(forms.Form):
    password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Nueva contraseña"}),
    )
    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repite la contraseña"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        if p1 and len(p1) < 8:
            raise forms.ValcidationError("La contraseña debe tener al menos 8 caracteres.")
        return cleaned_data
