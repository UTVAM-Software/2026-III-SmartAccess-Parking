from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from estacionamientos.models import Estacionamiento
from .storage import PrivateCaptureStorage
from usuarios.models import Vehiculo


class RegistroUso(models.Model):
    id_registro = models.BigAutoField(primary_key=True)
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        related_name="registros_uso",
        db_column="placa",
        to_field="placa",
    )
    estacionamiento = models.ForeignKey(
        Estacionamiento,
        on_delete=models.PROTECT,
        related_name="registros_uso",
        db_column="id_estacionamiento",
    )
    fecha = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField(null=True, blank=True)
    estado_acreditacion = models.CharField(max_length=30)
    autorizado = models.BooleanField(default=True)

    class Meta:
        db_table = 'registro_uso'
        verbose_name = 'registro de uso'
        verbose_name_plural = 'registros de uso'
        permissions = [
            (
                "change_registrouso_history",
                "Can edit historical usage records",
            ),
            (
                "delete_registrouso_history",
                "Can delete historical usage records",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("estacionamiento",),
                condition=Q(hora_salida__isnull=True),
                name="unique_active_use_per_estacionamiento",
            ),
            models.UniqueConstraint(
                fields=("vehiculo",),
                condition=Q(hora_salida__isnull=True),
                name="unique_active_use_per_vehiculo",
            ),
        ]

    def __str__(self) -> str:
        salida = self.hora_salida or "En curso"
        return (
            f"Registro {self.id_registro} · {self.vehiculo.placa} · "
            f"{self.fecha} {self.hora_entrada}–{salida}"
        )


class CapturaPlaca(models.Model):
    id_captura = models.BigAutoField(primary_key=True)
    registro_uso = models.ForeignKey(
        RegistroUso,
        on_delete=models.PROTECT,
        related_name="capturas_placa",
        db_column="id_registro",
    )
    placa_detectada = models.CharField(max_length=15)
    fecha_hora = models.DateTimeField()
    confianza = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    imagen = models.ImageField(
        upload_to='capturas_placa/',
        storage=PrivateCaptureStorage(),
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'captura_placa'
        verbose_name = 'captura de placa'
        verbose_name_plural = 'capturas de placa'

    def __str__(self) -> str:
        return f"Captura {self.id_captura} · {self.placa_detectada} · {self.fecha_hora}"


class Incidencia(models.Model):
    id_incidencia = models.BigAutoField(primary_key=True)
    registro_uso = models.ForeignKey(
        RegistroUso,
        on_delete=models.PROTECT,
        related_name="incidencias",
        db_column="id_registro",
    )
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()
    fecha_hora = models.DateTimeField()
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'incidencia'
        verbose_name = 'incidencia'
        verbose_name_plural = 'incidencias'

    def __str__(self) -> str:
        estado = "activa" if self.estado else "resuelta"
        return f"Incidencia {self.id_incidencia} · {self.tipo} · {estado}"


class Boleto(models.Model):
    """Boleto histórico o de entrada, sin lógica de cobro."""

    id_boleto = models.BigAutoField(primary_key=True)
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        related_name="boletos",
    )
    registro_uso = models.OneToOneField(
        RegistroUso,
        on_delete=models.PROTECT,
        related_name="boleto",
        null=True,
        blank=True,
    )
    numero_boleto = models.CharField(max_length=50, unique=True)
    fecha_entrada = models.DateTimeField()
    fecha_salida = models.DateTimeField(null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cargo_adicional = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    pagado = models.BooleanField(default=False)

    class Meta:
        db_table = "boleto"
        verbose_name = "boleto"
        verbose_name_plural = "boletos"

    def __str__(self) -> str:
        return str(self.numero_boleto)


class Pago(models.Model):
    """Conserva datos de pagos históricos; no procesa transacciones."""

    id_pago = models.BigAutoField(primary_key=True)
    boleto = models.OneToOneField(
        Boleto,
        on_delete=models.PROTECT,
        related_name="pago_historico",
    )
    fecha_pago = models.DateTimeField()
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=50)

    class Meta:
        db_table = "pago"
        verbose_name = "pago histórico"
        verbose_name_plural = "pagos históricos"

    def __str__(self) -> str:
        return f"Pago histórico {self.boleto}"


class IntentoAcceso(models.Model):
    """Registra decisiones de acceso, incluso cuando se rechazan."""

    class Resultado(models.TextChoices):
        AUTORIZADO = "AUTORIZADO", "Autorizado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    class FuenteCaptura(models.TextChoices):
        MANUAL = "MANUAL", "Captura manual"
        OCR = "OCR", "Lectura OCR"

    id_intento = models.BigAutoField(primary_key=True)
    plaza = models.ForeignKey(
        "estacionamientos.Plaza",
        on_delete=models.PROTECT,
        related_name="intentos_acceso",
        null=True,
        blank=True,
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    placa_capturada = models.CharField(max_length=20, blank=True, default="")
    imagen = models.ImageField(
        upload_to="intentos_acceso/",
        storage=PrivateCaptureStorage(),
        null=True,
        blank=True,
    )
    resultado = models.CharField(max_length=12, choices=Resultado.choices)
    motivo_rechazo = models.TextField(blank=True, default="")
    fuente_captura = models.CharField(
        max_length=10,
        choices=FuenteCaptura.choices,
        default=FuenteCaptura.MANUAL,
    )
    confianza_ocr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="intentos_acceso_operados",
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="intentos_acceso",
        null=True,
        blank=True,
    )
    acreditacion = models.ForeignKey(
        "usuarios.Acreditacion",
        on_delete=models.PROTECT,
        related_name="intentos_acceso",
        null=True,
        blank=True,
    )
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        related_name="intentos_acceso",
        null=True,
        blank=True,
    )
    estacionamiento = models.ForeignKey(
        Estacionamiento,
        on_delete=models.PROTECT,
        related_name="intentos_acceso",
        null=True,
        blank=True,
    )
    registro_uso = models.ForeignKey(
        RegistroUso,
        on_delete=models.PROTECT,
        related_name="intentos_acceso",
        null=True,
        blank=True,
    )
    boleto = models.ForeignKey(
        Boleto,
        on_delete=models.PROTECT,
        related_name="intentos_acceso",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "intento_acceso"
        verbose_name = "intento de acceso"
        verbose_name_plural = "intentos de acceso"
        permissions = [
            (
                "validate_plate_access",
                "Can validate whether a plate has a current disability accreditation",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(resultado="RECHAZADO") & ~Q(motivo_rechazo="")
                )
                | (
                    Q(resultado="AUTORIZADO")
                    & Q(motivo_rechazo="")
                    & ~Q(placa_capturada="")
                    & Q(plaza__isnull=False)
                    & Q(usuario__isnull=False)
                    & Q(acreditacion__isnull=False)
                    & Q(vehiculo__isnull=False)
                ),
                name="valid_access_attempt_result_relations",
            ),
        ]

    def __str__(self):
        placa = self.placa_capturada or "Sin placa"
        return f"{self.resultado} · {placa} · {self.fecha_hora:%Y-%m-%d %H:%M}"
