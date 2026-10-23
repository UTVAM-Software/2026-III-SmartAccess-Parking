from django import forms

from .models import Usuario, Vehiculo

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'correo_electronico', 'telefono', 'estado']

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = ['placa', 'usuario', 'modelo', 'estado']