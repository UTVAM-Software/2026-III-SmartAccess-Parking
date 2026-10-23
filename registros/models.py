from django.db import models

from estacionamientos.models import Estacionamiento
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

    class Meta:
        db_table = 'registro_uso'
        verbose_name = 'registro de uso'
        verbose_name_plural = 'registros de uso'

    def __str__(self):
        return f"Registro {self.id_registro} - {self.vehiculo}"


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
        imagen = models.ImageField(
            upload_to='capturas_placa/',
            null=True,
            blank=True
        )

        class Meta:
            db_table = 'captura_placa'
            verbose_name = 'captura de placa'
            verbose_name_plural = 'capturas de placa'

        def __str__(self):
            return f"Captura {self.id_captura} - {self.placa_detectada}"

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

    def __str__(self):
        return f"Incidencia {self.id_incidencia} - {self.tipo}"