from django import forms

from common.views import managed_plazas
from .models import Estacionamiento, Sensor


class EstacionamientoForm(forms.ModelForm):
    class Meta:
        model = Estacionamiento
        fields = [
            "numero_cajon",
            "plaza",
            "ubicacion",
            "accesible",
            "exclusivo_discapacidad",
            "activo",
        ]
        labels = {
            "numero_cajon": "Número de cajón",
            "plaza": "Plaza comercial",
            "ubicacion": "Ubicación",
            "accesible": "Accesible",
            "exclusivo_discapacidad": "Exclusivo para discapacidad",
            "activo": "Activo",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["plaza"].queryset = managed_plazas(user)

class SensorForm(forms.ModelForm):
    class Meta:
        model = Sensor
        fields = [
            "estacionamiento",
            "tipo_sensor",
            "estado",
            "estado_ocupacion",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["estacionamiento"].queryset = Estacionamiento.objects.filter(
                plaza__in=managed_plazas(user)
            ).select_related("plaza")
