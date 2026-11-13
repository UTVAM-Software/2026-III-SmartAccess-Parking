from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models


def default_plaza_id():
    """Use the pilot site for legacy integrations that still create bare stalls."""
    plaza, _ = Plaza.objects.get_or_create(
        nombre="Tizara",
        estado="Hidalgo",
        municipio="Tizayuca",
        defaults={"activa": True},
    )
    return plaza.pk


class Plaza(models.Model):
    """Sede comercial que agrupa cajones y operadores autorizados."""

    class Estado(models.TextChoices):
        HIDALGO = "Hidalgo", "Hidalgo"

    class Municipio(models.TextChoices):
        TIZAYUCA = "Tizayuca", "Tizayuca"

    nombre = models.CharField(max_length=100)
    estado = models.CharField(
        max_length=80,
        choices=Estado.choices,
        default=Estado.HIDALGO,
    )
    municipio = models.CharField(
        max_length=100,
        choices=Municipio.choices,
        default=Municipio.TIZAYUCA,
    )
    activa = models.BooleanField(default=True)
    administradores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="plazas_administradas",
        help_text=(
            "Operadores que pueden revisar datos y operar únicamente esta plaza."
        ),
    )
    personal_acceso = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="plazas_de_acceso",
        help_text=(
            "Personal de acceso que puede revisar placas únicamente en esta plaza."
        ),
    )

    class Meta:
        db_table = "plaza"
        verbose_name = "plaza"
        verbose_name_plural = "plazas"
        ordering = ("estado", "municipio", "nombre")
        constraints = [
            models.UniqueConstraint(
                fields=("nombre", "estado", "municipio"),
                name="unique_plaza_name_location",
            ),
        ]
        permissions = [
            (
                "view_operational_dashboard",
                "Can view the parking operations dashboard",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} · {self.municipio}, {self.estado}"


class Estacionamiento(models.Model):
    id_estacionamiento = models.BigAutoField(primary_key=True)
    numero_cajon = models.CharField(max_length=20, unique=True)
    plaza = models.ForeignKey(
        Plaza,
        on_delete=models.PROTECT,
        related_name="cajones",
        default=default_plaza_id,
    )
    ubicacion = models.CharField(max_length=100, blank=True, default="")
    accesible = models.BooleanField(default=False)
    exclusivo_discapacidad = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'estacionamiento'
        verbose_name = 'estacionamiento'
        verbose_name_plural = 'estacionamientos'

    def clean(self):
        super().clean()
        if self.exclusivo_discapacidad and not self.accesible:
            raise ValidationError(
                {
                    "accesible": (
                        "Un cajón exclusivo para discapacidad debe ser accesible."
                    )
                }
            )

    def __str__(self) -> str:
        disponibilidad = "Disponible" if self.estado else "No disponible"
        activacion = "Activo" if self.activo else "Inactivo"
        return f"Cajón {self.numero_cajon} · {disponibilidad} · {activacion}"


class Sensor(models.Model):
    id_sensor = models.BigAutoField(primary_key=True)
    estacionamiento = models.ForeignKey(
        Estacionamiento,
        on_delete=models.PROTECT,
        related_name="sensores",
        db_column="id_estacionamiento",
    )
    tipo_sensor = models.CharField(max_length=50)
    estado = models.BooleanField(default=True)
    estado_ocupacion = models.BooleanField(default=False)

    class Meta:
        db_table = 'sensor'
        verbose_name = 'sensor'
        verbose_name_plural = 'sensores'

    def __str__(self) -> str:
        estado = "activo" if self.estado else "inactivo"
        ocupacion = "ocupado" if self.estado_ocupacion else "libre"
        return f"Sensor {self.id_sensor} · {self.estacionamiento} · {estado}, {ocupacion}"
