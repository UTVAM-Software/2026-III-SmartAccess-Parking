from django import forms

from .models import Acreditacion, Usuario, Vehiculo

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "correo_electronico",
            "telefono",
            "estado",
        ]

class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = ["placa", "usuario", "modelo", "marca", "color", "estado"]


class AcreditacionForm(forms.ModelForm):
    class Meta:
        model = Acreditacion
        fields = [
            "usuario",
            "tipo",
            "documento",
            "fecha_validacion",
            "fecha_vencimiento",
            "estado",
        ]
        labels = {
            "usuario": "Usuario acreditado",
            "tipo": "Categoría",
            "documento": "Referencia del documento",
            "fecha_validacion": "Fecha de aprobación",
            "fecha_vencimiento": "Fecha de vencimiento (opcional)",
            "estado": "Aprobada",
        }
        widgets = {
            "fecha_validacion": forms.DateInput(attrs={"type": "date"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        approved = cleaned_data.get("estado")
        validation_date = cleaned_data.get("fecha_validacion")
        expiry_date = cleaned_data.get("fecha_vencimiento")

        if approved and not validation_date:
            self.add_error(
                "fecha_validacion",
                "Una acreditación aprobada requiere una fecha de validación.",
            )
        if validation_date and expiry_date and expiry_date < validation_date:
            self.add_error(
                "fecha_vencimiento",
                "La fecha de vencimiento no puede ser anterior a la validación.",
            )
        return cleaned_data
