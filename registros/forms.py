from django import forms
from django.core.exceptions import ValidationError

from .models import CapturaPlaca, Incidencia, RegistroUso


class RegistroUsoForm(forms.ModelForm):
    class Meta:
        model = RegistroUso
        fields = [
            "vehiculo",
            "estacionamiento",
            "fecha",
            "hora_entrada",
            "hora_salida",
            "estado_acreditacion",
        ]
        labels = {
            "vehiculo": "Vehículo (placa)",
            "estacionamiento": "Estacionamiento",
            "fecha": "Fecha",
            "hora_entrada": "Hora de entrada",
            "hora_salida": "Hora de salida (opcional)",
            "estado_acreditacion": "Estado de acreditación",
        }
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "hora_entrada": forms.TimeInput(attrs={"type": "time"}),
            "hora_salida": forms.TimeInput(attrs={"type": "time"}),
        }


class CapturaPlacaForm(forms.ModelForm):
    class Meta:
        model = CapturaPlaca
        fields = [
            "registro_uso",
            "placa_detectada",
            "fecha_hora",
            "imagen",
        ]
        labels = {
            "registro_uso": "Registro de uso",
            "placa_detectada": "Placa detectada",
            "fecha_hora": "Fecha y hora de captura",
            "imagen": "Imagen (opcional)",
        }
        widgets = {
            "fecha_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = [
            "registro_uso",
            "tipo",
            "descripcion",
            "fecha_hora",
            "estado",
        ]
        labels = {
            "registro_uso": "Registro de uso",
            "tipo": "Tipo de incidencia",
            "descripcion": "Descripción",
            "fecha_hora": "Fecha y hora",
            "estado": "Activa",
        }
        widgets = {
            "fecha_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

        


class IntentoAccesoForm(forms.Form):
    """Entrada manual de evidencia; el resultado lo determina el servidor."""

    placa_capturada = forms.CharField(
        label="Placa capturada o ingresada",
        max_length=20,
        required=False,
        strip=True,
        help_text="Simulación manual: no se ejecuta OCR ni se usa una cámara.",
    )
    imagen = forms.ImageField(
        label="Fotografía de la placa (opcional)",
        required=False,
    )

    def clean_placa_capturada(self):
        return self.cleaned_data["placa_capturada"].strip().upper()

    def clean_imagen(self):
        image = self.cleaned_data.get("imagen")
        if image and image.size > 5 * 1024 * 1024:
            raise ValidationError("La fotografía no puede superar 5 MB.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("placa_capturada") and not cleaned_data.get("imagen"):
            raise ValidationError("Ingresa una placa o adjunta una fotografía.")
        return cleaned_data