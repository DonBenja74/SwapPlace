from django import forms
from .models import Mensaje, Producto, Perfil


# -------------------------
# FORMULARIO DE CHAT
# -------------------------
class MensajeForm(forms.ModelForm):
    class Meta:
        model = Mensaje
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Escribe tu mensaje (máx. 500 caracteres)...',
                'maxlength': '500',
                'class': 'form-control'
            })
        }
        labels = {
            'contenido': ''
        }


# -------------------------
# FORMULARIO PRODUCTO
# -------------------------
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'imagen']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto',
                'maxlength': '100'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el producto...'
            }),
            'imagen': forms.FileInput(attrs={'class': 'form-control'})
        }


# -------------------------
# FORMULARIO SUSPENSIÓN ADMIN
# -------------------------
class SuspenderUsuarioForm(forms.Form):
    razon = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Razón de la suspensión'
        })
    )


# -------------------------
# FORMULARIO DE ADVERTENCIA
# -------------------------
class AdvertenciaForm(forms.Form):
    mensaje = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Describe la advertencia'
        })
    )


# -------------------------
# FORMULARIO DE CALIFICACIÓN (Opcional)
# -------------------------
class CalificacionForm(forms.Form):
    estrellas = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'type': 'number'
        })
    )

class ModerarUsuarioForm(forms.Form):
    usuario_id = forms.IntegerField(widget=forms.HiddenInput())
    accion = forms.ChoiceField(choices=[
        ('bloquear', 'Bloquear'),
        ('desbloquear', 'Desbloquear'),
    ])
