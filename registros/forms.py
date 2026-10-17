from django import forms

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
        widgets = {
            "fecha_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }