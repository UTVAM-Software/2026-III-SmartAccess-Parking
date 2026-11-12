"""Reglas transaccionales de autorización de entradas y registro de salidas."""

from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from estacionamientos.models import Estacionamiento, Sensor
from .models import Boleto, CapturaPlaca, IntentoAcceso, RegistroUso
from usuarios.models import Acreditacion, Vehiculo


def _record_rejection(
    operator,
    plate,
    image,
    reason,
    user=None,
    vehicle=None,
    accreditation=None,
):
    """Registra un rechazo sin asignar cajón, uso ni boleto."""
    attempt = IntentoAcceso.objects.create(
        operador=operator,
        placa_capturada=plate,
        usuario=user,
        vehiculo=vehicle,
        resultado=IntentoAcceso.Resultado.RECHAZADO,
        motivo_rechazo=reason,
        acreditacion=accreditation,
    )
    if image:
        attempt.imagen.save(image.name.rsplit("/", 1)[-1], image, save=True)
    return attempt


def process_manual_access(*, operator, placa_capturada, imagen=None):
    """Valida reglas de acceso y registra una decisión manual, sin OCR."""
    if not operator.is_authenticated or not operator.has_perm("registros.add_intentoacceso"):
        raise PermissionDenied("No tienes permiso para registrar intentos de acceso.")

    plate = (placa_capturada or "").strip().upper()
    try:
        with transaction.atomic():
            if not plate:
                return _record_rejection(
                    operator,
                    plate,
                    imagen,
                    "No se ingresó una placa y la simulación no incluye OCR.",
                )

            vehicles = list(
                Vehiculo.objects.select_for_update()
                .filter(placa__iexact=plate)
                .select_related("usuario", "usuario__acreditacion")
            )
            if len(vehicles) != 1:
                reason = (
                    "La placa coincide con más de un vehículo."
                    if vehicles
                    else "No hay un vehículo registrado con esa placa."
                )
                return _record_rejection(operator, plate, imagen, reason)

            vehicle = vehicles[0]
            user = vehicle.usuario
            if not user.estado or not vehicle.estado:
                return _record_rejection(
                    operator,
                    plate,
                    imagen,
                    "El usuario o el vehículo está inactivo.",
                    user,
                    vehicle,
                )

            if RegistroUso.objects.filter(
                vehiculo=vehicle,
                hora_salida__isnull=True,
            ).exists():
                return _record_rejection(
                    operator,
                    plate,
                    imagen,
                    "El vehículo ya tiene una entrada activa.",
                    user,
                    vehicle,
                )

            try:
                accreditation = user.acreditacion
            except Acreditacion.DoesNotExist:
                accreditation = None
            today = timezone.localdate()
            if not accreditation or not accreditation.esta_vigente(today):
                return _record_rejection(
                    operator,
                    plate,
                    imagen,
                    "El usuario no tiene una acreditación DISCAPACIDAD aprobada y vigente.",
                    user,
                    vehicle,
                    accreditation,
                )

            active_uses = RegistroUso.objects.filter(
                estacionamiento_id=OuterRef("pk"),
                hora_salida__isnull=True,
            )
            active_sensors = Sensor.objects.filter(
                estacionamiento_id=OuterRef("pk"),
                estado=True,
                estado_ocupacion=True,
            )
            available_spaces = (
                Estacionamiento.objects.select_for_update()
                .filter(estado=True, activo=True)
                .annotate(ocupado=Exists(active_uses))
                .filter(ocupado=False)
            )
            spaces = list(
                available_spaces.annotate(sensor_ocupado=Exists(active_sensors))
                .filter(sensor_ocupado=False)
                .order_by("-exclusivo_discapacidad", "id_estacionamiento")
            )
            if not spaces:
                reason = (
                    "El sensor reporta ocupación y el espacio requiere revisión."
                    if available_spaces.annotate(
                        sensor_ocupado=Exists(active_sensors)
                    ).filter(sensor_ocupado=True).exists()
                    else "No hay cajones disponibles."
                )
                return _record_rejection(
                    operator,
                    plate,
                    imagen,
                    reason,
                    user,
                    vehicle,
                    accreditation,
                )

            space = spaces[0]
            now = timezone.localtime()
            use = RegistroUso.objects.create(
                vehiculo=vehicle,
                estacionamiento=space,
                fecha=now.date(),
                hora_entrada=now.time().replace(tzinfo=None),
                estado_acreditacion="DISCAPACIDAD vigente",
                autorizado=True,
            )
            ticket = Boleto.objects.create(
                vehiculo=vehicle,
                registro_uso=use,
                numero_boleto=uuid4().hex,
                fecha_entrada=now,
                monto=0,
                cargo_adicional=0,
                pagado=False,
            )
            space.estado = False
            space.save(update_fields=("estado",))
            attempt = IntentoAcceso.objects.create(
                operador=operator,
                placa_capturada=plate,
                resultado=IntentoAcceso.Resultado.AUTORIZADO,
                motivo_rechazo="",
                usuario=user,
                acreditacion=accreditation,
                vehiculo=vehicle,
                estacionamiento=space,
                registro_uso=use,
                boleto=ticket,
            )
            if imagen:
                attempt.imagen.save(
                    imagen.name.rsplit("/", 1)[-1], imagen, save=True
                )
                CapturaPlaca.objects.create(
                    registro_uso=use,
                    placa_detectada=plate,
                    fecha_hora=now,
                    imagen=attempt.imagen.name,
                )
            return attempt
    except IntegrityError as error:
        message = str(error).casefold()
        if "unique" not in message and "duplicate key" not in message:
            raise
        return _record_rejection(
            operator,
            plate,
            imagen,
            "El vehículo ya tiene una entrada activa o el cajón se ocupó simultáneamente.",
        )


def register_exit(*, operator, registro_id):
    """Cierra una entrada activa y libera el cajón en la misma transacción."""
    if not operator.is_authenticated or not operator.has_perm("registros.change_registrouso"):
        raise PermissionDenied("No tienes permiso para registrar salidas.")

    with transaction.atomic():
        use = RegistroUso.objects.select_for_update().get(pk=registro_id)
        if use.hora_salida is not None:
            raise ValidationError("El registro ya tiene una salida registrada.")
        now = timezone.localtime()
        use.hora_salida = now.time().replace(tzinfo=None)
        use.save(update_fields=("hora_salida",))

        ticket = Boleto.objects.select_for_update().filter(registro_uso=use).first()
        if ticket:
            ticket.fecha_salida = now
            ticket.save(update_fields=("fecha_salida",))

        space = Estacionamiento.objects.select_for_update().get(
            pk=use.estacionamiento_id
        )
        other_active_uses = RegistroUso.objects.filter(
            estacionamiento=space,
            hora_salida__isnull=True,
        ).exists()
        occupied_sensor = Sensor.objects.select_for_update().filter(
            estacionamiento=space,
            estado=True,
            estado_ocupacion=True,
        ).exists()
        if space.activo and not other_active_uses and not occupied_sensor:
            space.estado = True
            space.save(update_fields=("estado",))
        return use
