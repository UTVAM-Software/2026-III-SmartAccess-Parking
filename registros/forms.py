from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.views import managed_plazas
from estacionamientos.models import Estacionamiento, Plaza
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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            plazas = managed_plazas(user)
            self.fields["vehiculo"].queryset = self.fields["vehiculo"].queryset.filter(
                usuario__plazas__in=plazas
            ).distinct()
            self.fields["estacionamiento"].queryset = Estacionamiento.objects.filter(
                plaza__in=plazas
            )
        if self.instance.pk:
            for field_name in (
                "vehiculo",
                "estacionamiento",
                "fecha",
                "hora_entrada",
                "hora_salida",
            ):
                self.fields[field_name].disabled = True
            self.fields["estado_acreditacion"].help_text = (
                "Los datos de entrada y salida se conservan como historial."
            )


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

    def clean_placa_detectada(self):
        return self.cleaned_data["placa_detectada"].strip().upper()

    def clean_imagen(self):
        image = self.cleaned_data.get("imagen")
        if image and image.size > 5 * 1024 * 1024:
            raise ValidationError("La fotografía no puede superar 5 MB.")
        return image

    def clean_fecha_hora(self):
        captured_at = self.cleaned_data["fecha_hora"]
        if captured_at > timezone.now():
            raise ValidationError("La fecha de captura no puede estar en el futuro.")
        return captured_at

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["registro_uso"].queryset = RegistroUso.objects.filter(
                estacionamiento__plaza__in=managed_plazas(user)
            )


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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["registro_uso"].queryset = RegistroUso.objects.filter(
                estacionamiento__plaza__in=managed_plazas(user)
            )

class IntentoAccesoForm(forms.Form):
    """Registra una entrada manual o toma una placa de una fotografía."""

    placa_capturada = forms.CharField(
        label="Placa (opcional si adjuntas una fotografía)",
        max_length=20,
        required=False,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ej. ABC-1234",
                "autocomplete": "off",
                "autofocus": True,
                "spellcheck": "false",
            }
        ),
        help_text=(
            "Si la dejas vacía, OCR propondrá una placa que deberás revisar y "
            "confirmar. También puedes escribirla directamente."
        ),
    )
    plaza = forms.ModelChoiceField(
        label="Plaza donde se valida el acceso",
        queryset=Plaza.objects.none(),
    )
    imagen = forms.ImageField(
        label="Fotografía del vehículo o su placa (opcional)",
        required=False,
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/*", "capture": "environment"}
        ),
        help_text=(
            "Puedes tomar una foto con el celular o elegir un archivo. Para que "
            "el sistema lea la placa, déjala vacía y confirma la propuesta."
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["plaza"].queryset = managed_plazas(user)
            if self.fields["plaza"].queryset.count() == 1:
                self.fields["plaza"].initial = self.fields["plaza"].queryset.first()

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
