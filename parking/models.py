
"""Aliases temporales a modelos canónicos; las tablas legacy quedan archivadas."""

from estacionamientos.models import Estacionamiento, Sensor
from registros.models import Boleto, CapturaPlaca, Incidencia, IntentoAcceso, Pago, RegistroUso
from usuarios.models import Acreditacion, Usuario, Vehiculo