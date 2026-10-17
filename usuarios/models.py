from django.db import models

class Usuario(models.Model):
    id_usuario =models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    correo_electronico = models.EmailField()
    telefono = models.CharField(max_length=20)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.nombre

class Vehiculo(models.Model):
    placa = models.CharField(max_length=15, primary_key=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="vehiculos",
        db_column="id_usuario",
    )
    modelo = models.CharField(max_length=80)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'vehiculo'
        verbose_name = 'vehiculo'
        verbose_name_plural = 'vehiculos'

    def __str__(self):
        return self.placa