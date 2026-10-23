from django import forms

from .models import Estacionamiento, Sensor


class EstacionamientoForm(forms.ModelForm):
    class Meta:
        model = Estacionamiento
        fields = ["numero_cajon", "estado"]


class SensorForm(forms.ModelForm):
    class Meta:
        model = Sensor
        fields = [
            "estacionamiento",
            "tipo_sensor",
            "estado",
            "estado_ocupacion",
        ]