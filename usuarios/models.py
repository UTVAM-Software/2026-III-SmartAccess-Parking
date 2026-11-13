from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from .storage import PrivateDocumentStorage


class Usuario(models.Model):
    id_usuario = models.BigAutoField(primary_key=True)
    cuenta = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="perfil_estacionamiento",
        null=True,
        blank=True,
    )
    plazas = models.ManyToManyField(
        "estacionamientos.Plaza",
        blank=True,
        related_name="usuarios",
        help_text="Plazas donde la persona solicita utilizar cajones accesibles.",
    )
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=100, blank=True, default="")
    apellido_materno = models.CharField(max_length=100, blank=True, default="")
    correo_electronico = models.EmailField()
    telefono = models.CharField(max_length=20)
    estado = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self) -> str:
        nombre_completo = " ".join(
            parte
            for parte in (
                self.nombre,
                self.apellido_paterno,
                self.apellido_materno,
            )
            if parte
        )
        return nombre_completo


class Vehiculo(models.Model):
    placa = models.CharField(max_length=15, primary_key=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="vehiculos",
        db_column="id_usuario",
    )
    modelo = models.CharField(max_length=80)
    marca = models.CharField(max_length=50, blank=True, default="")
    color = models.CharField(max_length=30, blank=True, default="")
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'vehiculo'
        verbose_name = 'vehiculo'
        verbose_name_plural = 'vehiculos'

    def clean(self):
        super().clean()
        existing = (
            type(self).objects.filter(pk=self.pk)
            .values("placa", "usuario_id")
            .first()
            if self.pk
            else None
        )
        previous_plate = existing["placa"] if existing else None
        entered_plate = (self.placa or "").strip()
        normalized_plate = entered_plate.upper()
        if previous_plate and entered_plate == previous_plate:
            self.placa = previous_plate
        elif previous_plate and normalized_plate != previous_plate:
            raise ValidationError(
                {"placa": "La placa no se puede cambiar después del registro."}
            )
        else:
            self.placa = normalized_plate
        duplicates = type(self).objects.filter(placa__iexact=self.placa)
        if self.pk:
            duplicates = duplicates.exclude(pk=self.pk)
        if self.placa and duplicates.exists():
            raise ValidationError(
                {"placa": "Ya existe un vehículo con esa placa."}
            )
        if self.usuario_id and (
            existing is None or existing["usuario_id"] != self.usuario_id
        ):
            if type(self).objects.filter(usuario_id=self.usuario_id).count() >= 3:
                raise ValidationError(
                    {"usuario": "Cada persona puede registrar hasta 3 vehículos."}
                )

    def save(self, *args, **kwargs):
        normalized_plate = (self.placa or "").strip().upper()
        existing = (
            type(self).objects.filter(pk=self.pk)
            .values("placa", "usuario_id")
            .first()
            if self.pk
            else None
        )
        previous_plate = existing["placa"] if existing else None
        if self.usuario_id and (
            existing is None or existing["usuario_id"] != self.usuario_id
        ):
            if type(self).objects.filter(usuario_id=self.usuario_id).count() >= 3:
                raise ValidationError(
                    {"usuario": "Cada persona puede registrar hasta 3 vehículos."}
                )
            if previous_plate and previous_plate != self.placa:
                raise ValidationError(
                    "No se puede cambiar la placa después del registro."
                )
        normalized_plate = previous_plate or normalized_plate
        duplicates = type(self).objects.filter(placa__iexact=normalized_plate)
        if self.pk:
            duplicates = duplicates.exclude(pk=self.pk)
        if duplicates.exists():
            raise ValidationError("Ya existe un vehículo con esa placa.")
        self.placa = normalized_plate
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.placa} · {self.marca} {self.modelo} · {self.usuario}"


class Acreditacion(models.Model):
    """Acreditación de discapacidad asociada a un usuario canónico."""

    class Tipo(models.TextChoices):
        DISCAPACIDAD = "DISCAPACIDAD", "Discapacidad"

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.PROTECT,
        related_name="acreditacion",
    )
    tipo = models.CharField(max_length=32, choices=Tipo.choices)
    documento = models.CharField(max_length=255, blank=True, default="")
    documento_imagen = models.ImageField(
        upload_to="documentos_acreditacion/",
        storage=PrivateDocumentStorage(),
        null=True,
        blank=True,
    )
    fecha_validacion = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.BooleanField(default=False)

    class Meta:
        db_table = "acreditacion"
        verbose_name = "acreditación"
        verbose_name_plural = "acreditaciones"
        constraints = [
            models.CheckConstraint(
                condition=Q(tipo="DISCAPACIDAD"),
                name="acreditacion_solo_discapacidad",
            ),
        ]

    def clean(self):
        super().clean()
        if self.estado and not self.fecha_validacion:
            raise ValidationError(
                {
                    "fecha_validacion": (
                        "Una acreditación aprobada requiere una fecha de validación."
                    )
                }
            )
        if self.fecha_validacion and self.fecha_validacion > timezone.localdate():
            raise ValidationError(
                {
                    "fecha_validacion": (
                        "La fecha de validación no puede estar en el futuro."
                    )
                }
            )
        if (
            self.fecha_validacion
            and self.fecha_vencimiento
            and self.fecha_vencimiento < self.fecha_validacion
        ):
            raise ValidationError(
                {
                    "fecha_vencimiento": (
                        "La fecha de vencimiento no puede ser anterior a la validación."
                    )
                }
            )

    def esta_vigente(self, fecha=None):
        """Comprueba aprobación, validación y vencimiento de la acreditación."""
        fecha = fecha or timezone.localdate()
        return (
            self.estado
            and self.tipo == self.Tipo.DISCAPACIDAD
            and self.fecha_validacion is not None
            and self.fecha_validacion <= fecha
            and (
                self.fecha_vencimiento is None
                or self.fecha_vencimiento >= fecha
            )
        )

    def __str__(self) -> str:
        estado = "Aprobada y vigente" if self.esta_vigente() else "No vigente"
        return f"Acreditación de {self.usuario} · {estado}"
