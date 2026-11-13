"""Reglas para mantener sincronizada la disponibilidad de los cajones."""

from django.db import transaction

from .models import Estacionamiento, Sensor


@transaction.atomic
def synchronize_availability(estacionamiento_id):
    """Recalcula disponibilidad usando activación, entradas y sensores."""
    from registros.models import RegistroUso

    space = Estacionamiento.objects.select_for_update().get(pk=estacionamiento_id)
    has_active_use = RegistroUso.objects.filter(
        estacionamiento_id=space.pk,
        hora_salida__isnull=True,
    ).exists()
    occupied_sensor = Sensor.objects.filter(
        estacionamiento_id=space.pk,
        estado=True,
        estado_ocupacion=True,
    ).exists()
    available = space.activo and not has_active_use and not occupied_sensor
    if space.estado != available:
        space.estado = available
        space.save(update_fields=("estado",))
    return space
