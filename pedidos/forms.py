# pedidos/forms.py
from django import forms
from .models import Pago


class CheckoutForm(forms.Form):
    """Información de contacto, dirección y método de pago del checkout."""

    nombre_receptor = forms.CharField(label="Nombre completo", max_length=200)
    correo = forms.EmailField(label="Correo electrónico")
    telefono_contacto = forms.CharField(label="Teléfono", max_length=15)
    pais = forms.CharField(label="País", max_length=2, initial="MX", widget=forms.HiddenInput)
    estado = forms.CharField(label="Estado", max_length=100)
    municipio = forms.CharField(label="Municipio / Ciudad", max_length=100)
    codigo_postal = forms.CharField(label="Código postal", max_length=10)
    colonia = forms.CharField(label="Colonia", max_length=100)
    calle = forms.CharField(label="Calle", max_length=200)
    numero_exterior = forms.CharField(label="Número exterior", max_length=10)
    numero_interior = forms.CharField(label="Número interior", max_length=10, required=False)
    referencias = forms.CharField(label="Referencias de entrega", required=False, widget=forms.Textarea)
    transportista = forms.CharField(widget=forms.HiddenInput)
    servicio = forms.CharField(widget=forms.HiddenInput)
    metodo_pago = forms.ChoiceField(label="Método de pago", choices=Pago.METODOS_PAGO)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["metodo_pago"].widget = forms.RadioSelect(
            choices=self.fields["metodo_pago"].choices,
            attrs={"class": "form-check-input"},
        )

    def clean_pais(self):
        # Agrivale únicamente opera envíos nacionales en México.
        return "MX"

class PagoForm(forms.ModelForm):
    """
    Este formulario se usa cuando el usuario inicia el pedido y 
    selecciona cómo va a pagar (Transferencia o OXXO).
    """
    class Meta:
        model = Pago
        fields = ['metodo']  # Solo pedimos el método, lo demás se gestiona después
        widgets = {
            'metodo': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'metodo': 'Método de pago',
        }

class ComprobanteForm(forms.ModelForm):
    """
    Este formulario se usa cuando el usuario ya pagó y 
    sube la foto del ticket o comprobante de transferencia.
    """
    class Meta:
        model = Pago
        fields = ['comprobante']
        widgets = {
            'comprobante': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.pdf'
            }),
        }
        labels = {
            'comprobante': 'Sube tu comprobante de pago',
        }
    
    def clean_comprobante(self):
        """
        Validación personalizada para el archivo subido
        """
        comprobante = self.cleaned_data.get('comprobante')
        
        if comprobante:
            # 1. Validar tamaño máximo (5MB = 5 * 1024 * 1024 bytes)
            max_size = 5 * 1024 * 1024  # 5MB
            if comprobante.size > max_size:
                raise forms.ValidationError(
                    'El archivo es demasiado grande. El tamaño máximo permitido es 5MB.'
                )
            
            # 2. Validar extensiones permitidas
            allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
            file_extension = comprobante.name.split('.')[-1].lower()
            
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f'Formato no válido. Solo se permiten: {", ".join(allowed_extensions)}'
                )
            
            # 3. Validar tipo de contenido (seguridad adicional)
            content_type = comprobante.content_type
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']
            
            if content_type not in allowed_types:
                raise forms.ValidationError(
                    'Tipo de archivo no válido. Solo se permiten imágenes JPG, PNG y PDF.'
                )
        
        return comprobante
