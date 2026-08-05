from django import forms
from .models import ComentarioProducto

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = ComentarioProducto
        fields = ['calificacion', 'titulo', 'comentario', 'imagen_1', 'imagen_2', 'imagen_3']
        widgets = {
            'calificacion': forms.RadioSelect(choices=[
                (5, '⭐⭐⭐⭐⭐ Excelente'),
                (4, '⭐⭐⭐⭐ Bueno'),
                (3, '⭐⭐⭐ Regular'),
                (2, '⭐⭐ Malo'),
                (1, '⭐ Muy malo')
            ]),
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Excelente producto, lo recomiendo'
            }),
            'comentario': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Cuéntanos tu experiencia con este producto...'
            }),
            'imagen_1': forms.FileInput(attrs={'class': 'form-control'}),
            'imagen_2': forms.FileInput(attrs={'class': 'form-control'}),
            'imagen_3': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'calificacion': '¿Cómo calificas este producto?',
            'titulo': 'Título de tu comentario (opcional)',
            'comentario': 'Tu opinión',
            'imagen_1': 'Foto 1 (opcional)',
            'imagen_2': 'Foto 2 (opcional)',
            'imagen_3': 'Foto 3 (opcional)',
        }