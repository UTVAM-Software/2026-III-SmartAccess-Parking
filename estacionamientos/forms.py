from django import forms

from .models import Estacionamiento, Sensor


class EstacionamientoForm(forms.ModelForm):
    class Meta:
        model = Estacionamiento
        fields = [
            "numero_cajon",
            "ubicacion",
            "accesible",
            "exclusivo_discapacidad",
            "activo",
            "estado",
        ]
        labels = {
            "numero_cajon": "Número de cajón",
            "ubicacion": "Ubicación",
            "accesible": "Accesible",
            "exclusivo_discapacidad": "Exclusivo para discapacidad",
            "activo": "Activo",
            "estado": "Disponible",
        }


class SensorForm(forms.ModelForm):
    class Meta:
        model = Sensor
        fields = [
            "estacionamiento",
            "tipo_sensor",
            "estado",
            "estado_ocupacion",
        ]