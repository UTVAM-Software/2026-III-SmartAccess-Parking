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