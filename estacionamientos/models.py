from django.db import models


class Estacionamiento(models.Model):
    id_estacionamiento = models.BigAutoField(primary_key=True)
    numero_cajon = models.CharField(max_length=20, unique=True)
    ubicacion = models.CharField(max_length=100, blank=True, default="")
    accesible = models.BooleanField(default=False)
    exclusivo_discapacidad = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'estacionamiento'
        verbose_name = 'estacionamiento'
        verbose_name_plural = 'estacionamientos'

    def __str__(self) -> str:
        return f"Cajón {self.numero_cajon}"


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
        return f"Sensor {self.id_sensor} - {self.estacionamiento}"
