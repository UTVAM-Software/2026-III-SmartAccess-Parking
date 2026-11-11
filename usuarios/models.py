from django.db import models
from django.db.models import Q
from django.utils import timezone


class Usuario(models.Model):
    id_usuario = models.BigAutoField(primary_key=True)
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
        return str(self.nombre)


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

    def __str__(self) -> str:
        return str(self.placa)


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
    documento = models.CharField(max_length=255)
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

    def esta_vigente(self, fecha=None):
        """Comprueba aprobación, validación y vencimiento de la acreditación."""
        fecha = fecha or timezone.localdate()
        return (
            self.estado
            and self.tipo == self.Tipo.DISCAPACIDAD
            and self.fecha_validacion is not None
            and (
                self.fecha_vencimiento is None
                or self.fecha_vencimiento >= fecha
            )
        )

    def __str__(self) -> str:
        return f"Acreditación de {self.usuario}"
