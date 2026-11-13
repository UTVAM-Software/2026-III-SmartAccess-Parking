from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from common.views import managed_plazas
from estacionamientos.models import Plaza
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
            "plazas",
            "estado",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.operator = user
        self._outside_scope_plaza_ids = []
        if user is not None:
            managed = managed_plazas(user)
            self.fields["plazas"].queryset = managed
            if self.instance.pk and not user.is_superuser:
                self._outside_scope_plaza_ids = list(
                    self.instance.plazas.exclude(pk__in=managed).values_list(
                        "pk", flat=True
                    )
                )

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit and self._outside_scope_plaza_ids:
            instance.plazas.add(*self._outside_scope_plaza_ids)
        return instance


class VehiculoForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = ["placa", "usuario", "modelo", "marca", "color", "estado"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["usuario"].queryset = Usuario.objects.filter(
                plazas__in=managed_plazas(user)
            ).distinct()
        if self.instance.pk:
            self.fields["placa"].disabled = True
            self.fields["placa"].help_text = (
                "La placa no se puede cambiar después de registrar el vehículo."
            )

    def clean_placa(self):
        if self.instance.pk:
            return self.instance.placa
        return self.cleaned_data["placa"].strip().upper()


class VehiculoCuentaForm(forms.ModelForm):
    class Meta:
        model = Vehiculo
        fields = ["placa", "marca", "modelo", "color"]
        labels = {
            "placa": "Placa del vehículo",
            "marca": "Marca",
            "modelo": "Modelo",
            "color": "Color",
        }

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.fields["placa"].help_text = (
            "La placa se guarda en mayúsculas y no se podrá cambiar después."
        )

    def clean_placa(self):
        plate = self.cleaned_data["placa"].strip().upper()
        if Vehiculo.objects.filter(placa__iexact=plate).exists():
            raise forms.ValidationError("Esta placa ya está registrada.")
        return plate

    def clean(self):
        cleaned_data = super().clean()
        if (
            self.profile
            and self.profile.vehiculos.count() >= 3
        ):
            raise forms.ValidationError(
                "Ya registraste el máximo de 3 vehículos permitidos."
            )
        return cleaned_data


class AcreditacionForm(forms.ModelForm):
    class Meta:
        model = Acreditacion
        fields = [
            "usuario",
            "tipo",
            "fecha_validacion",
            "fecha_vencimiento",
            "estado",
        ]
        labels = {
            "usuario": "Usuario acreditado",
            "tipo": "Categoría",
            "fecha_validacion": "Fecha de aprobación",
            "fecha_vencimiento": "Fecha de vencimiento (opcional)",
            "estado": "Aprobada",
        }
        widgets = {
            "fecha_validacion": forms.DateInput(attrs={"type": "date"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["usuario"].queryset = Usuario.objects.filter(
                plazas__in=managed_plazas(user)
            ).distinct()


class RegistroPublicoForm(UserCreationForm):
    """Crea una cuenta común y los datos que administración revisará."""

    nombre = forms.CharField(label="Nombre", max_length=100)
    apellido_paterno = forms.CharField(
        label="Apellido paterno",
        max_length=100,
        required=False,
    )
    apellido_materno = forms.CharField(
        label="Apellido materno",
        max_length=100,
        required=False,
    )
    telefono = forms.CharField(label="Teléfono", max_length=20)
    placa = forms.CharField(label="Placa del vehículo", max_length=15)
    marca = forms.CharField(label="Marca", max_length=50, required=False)
    modelo = forms.CharField(label="Modelo", max_length=80)
    color = forms.CharField(label="Color", max_length=30, required=False)
    estado = forms.ChoiceField(
        label="Estado",
        choices=[("", "Selecciona un estado"), *Plaza.Estado.choices],
    )
    municipio = forms.ChoiceField(
        label="Municipio",
        choices=[("", "Selecciona un municipio"), *Plaza.Municipio.choices],
    )
    plazas = forms.ModelMultipleChoiceField(
        label="Plazas donde solicitas acceso",
        queryset=Plaza.objects.none(),
        required=True,
        widget=forms.SelectMultiple(attrs={"size": 4}),
        help_text=(
            "Puedes elegir varias plazas. En una computadora usa Ctrl para seleccionar "
            "más de una; la solicitud queda pendiente de aprobación."
        ),
    )

    documento_imagen = forms.ImageField(
        label="Foto del documento de acreditación",
        help_text=(
            "Sube una foto clara del documento. Solo el personal asignado a la plaza "
            "podrá revisarla. Máximo 5 MB."
        ),
    )

    field_order = (
        "username",
        "email",
        "nombre",
        "apellido_paterno",
        "apellido_materno",
        "telefono",
        "estado",
        "municipio",
        "plazas",
        "placa",
        "marca",
        "modelo",
        "color",
        "documento_imagen",
        "password1",
        "password2",
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Nombre de usuario"
        self.fields["email"].label = "Correo electrónico"
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"
        self.fields["username"].help_text = ""
        selected_state = self.data.get("estado") or self.initial.get("estado")
        selected_municipality = (
            self.data.get("municipio") or self.initial.get("municipio")
        )
        if selected_state and selected_municipality:
            self.fields["plazas"].queryset = Plaza.objects.filter(
                estado=selected_state,
                municipio=selected_municipality,
                activa=True,
            ).order_by("nombre")
        self.fields["documento_imagen"].required = True
        self.order_fields(self.field_order)

    def clean_documento_imagen(self):
        image = self.cleaned_data.get("documento_imagen")
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La fotografía no puede superar 5 MB.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get("estado")
        municipality = cleaned_data.get("municipio")
        plazas = cleaned_data.get("plazas")
        if state and municipality and plazas:
            if plazas.exclude(estado=state, municipio=municipality).exists():
                self.add_error(
                    "plazas",
                    "Selecciona plazas que pertenezcan al estado y municipio elegidos.",
                )
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        if Usuario.objects.filter(correo_electronico__iexact=email).exists():
            raise forms.ValidationError(
                "Ese correo ya está registrado. Contacta a administración para vincular tu cuenta."
            )
        return email

    def clean_placa(self):
        plate = self.cleaned_data["placa"].strip().upper()
        if Vehiculo.objects.filter(placa__iexact=plate).exists():
            raise forms.ValidationError(
                "Ya existe un vehículo registrado con esa placa."
            )
        return plate
