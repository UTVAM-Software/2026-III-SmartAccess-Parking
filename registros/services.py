"""Reglas transaccionales de autorización de entradas y registro de salidas."""

from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from common.views import can_manage_plaza, managed_plazas
from estacionamientos.models import Estacionamiento, Plaza, Sensor
from estacionamientos.services import synchronize_availability
from .models import Boleto, CapturaPlaca, IntentoAcceso, RegistroUso
from usuarios.models import Acreditacion, Vehiculo


def validate_disability_plate(
    *,
    operator,
    plaza,
    placa_capturada,
    imagen=None,
    fuente_captura=IntentoAcceso.FuenteCaptura.MANUAL,
    confianza_ocr=None,
):
    """Check a plate's current accreditation without opening a parking stay."""
    if (
        not operator.is_authenticated
        or not operator.has_perm("registros.validate_plate_access")
    ):
        raise PermissionDenied("No tienes permiso para validar placas.")
    if not isinstance(plaza, Plaza) or not plaza.activa:
        raise ValidationError("Selecciona una plaza activa para validar la placa.")
    if not can_manage_plaza(operator, plaza):
        raise PermissionDenied("No tienes asignada la plaza seleccionada.")

    plate = (placa_capturada or "").strip().upper()

    def save_result(result, reason="", user=None, vehicle=None, accreditation=None):
        attempt = IntentoAcceso.objects.create(
            operador=operator,
            plaza=plaza,
            placa_capturada=plate,
            usuario=user,
            vehiculo=vehicle,
            acreditacion=accreditation,
            resultado=result,
            motivo_rechazo=reason,
            fuente_captura=fuente_captura,
            confianza_ocr=confianza_ocr,
        )
        if imagen:
            attempt.imagen.save(
                imagen.name.rsplit("/", 1)[-1],
                imagen,
                save=True,
            )
        return attempt

    def reject(reason, user=None, vehicle=None, accreditation=None):
        return save_result(
            IntentoAcceso.Resultado.RECHAZADO,
            reason,
            user,
            vehicle,
            accreditation,
        )

    if not plate:
        return reject("No se obtuvo una placa. Escríbela manualmente.")

    vehicles = list(
        Vehiculo.objects.select_related(
            "usuario",
            "usuario__cuenta",
            "usuario__acreditacion",
        ).filter(placa__iexact=plate)[:2]
    )
    if not vehicles:
        return reject("La placa no está registrada en el sistema.")
    if len(vehicles) > 1:
        return reject("La placa coincide con más de un vehículo registrado.")

    vehicle = vehicles[0]
    user = vehicle.usuario
    if not user.plazas.filter(pk=plaza.pk).exists():
        return reject(
            "La persona no solicitó acceso para esta plaza.",
            user,
            vehicle,
        )
    if not user.estado or not vehicle.estado:
        return reject("La cuenta o el vehículo está inactivo.", user, vehicle)
    if user.cuenta_id and not user.cuenta.is_active:
        return reject("La cuenta de la persona está desactivada.", user, vehicle)

    try:
        accreditation = user.acreditacion
    except Acreditacion.DoesNotExist:
        accreditation = None
    if accreditation is None or not accreditation.esta_vigente():
        return reject(
            "La acreditación está pendiente, vencida o no fue aprobada.",
            user,
            vehicle,
            accreditation,
        )

    return save_result(
        IntentoAcceso.Resultado.AUTORIZADO,
        user=user,
        vehicle=vehicle,
        accreditation=accreditation,
    )


def _record_rejection(
    operator,
    plate,
    image,
    reason,
    user=None,
    vehicle=None,
    accreditation=None,
    plaza=None,
    fuente_captura=IntentoAcceso.FuenteCaptura.MANUAL,
    confianza_ocr=None,
):
    """Registra un rechazo sin asignar cajón, uso ni boleto."""
    attempt = IntentoAcceso.objects.create(
        operador=operator,
        plaza=plaza,
        placa_capturada=plate,
        usuario=user,
        vehiculo=vehicle,
        resultado=IntentoAcceso.Resultado.RECHAZADO,
        motivo_rechazo=reason,
        acreditacion=accreditation,
        fuente_captura=fuente_captura,
        confianza_ocr=confianza_ocr,
    )
    if image:
        attempt.imagen.save(image.name.rsplit("/", 1)[-1], image, save=True)
    return attempt


def process_manual_access(
    *,
    operator,
    plaza,
    placa_capturada,
    imagen=None,
    fuente_captura=IntentoAcceso.FuenteCaptura.MANUAL,
    confianza_ocr=None,
):
    """Valida la placa capturada y registra autorización o rechazo."""
    if not operator.is_authenticated or not operator.has_perm("registros.add_intentoacceso"):
        raise PermissionDenied("No tienes permiso para registrar intentos de acceso.")
    if not isinstance(plaza, Plaza) or not plaza.activa:
        raise ValidationError("Selecciona una plaza activa para validar el acceso.")
    if not can_manage_plaza(operator, plaza):
        raise PermissionDenied("No tienes asignada la plaza seleccionada.")

    plate = (placa_capturada or "").strip().upper()

    def reject(reason, user=None, vehicle=None, accreditation=None):
        return _record_rejection(
            operator,
            plate,
            imagen,
            reason,
            user,
            vehicle,
            accreditation,
            plaza,
            fuente_captura,
            confianza_ocr,
        )

    try:
        with transaction.atomic():
            if not plate:
                return reject("No se pudo obtener una placa para validar.")

            vehicles = list(
                Vehiculo.objects.select_for_update()
                .filter(placa__iexact=plate)
                .select_related(
                    "usuario",
                    "usuario__cuenta",
                    "usuario__acreditacion",
                )
            )
            if len(vehicles) != 1:
                reason = (
                    "La placa coincide con más de un vehículo."
                    if vehicles
                    else "No hay un vehículo registrado con esa placa."
                )
                return reject(reason)

            vehicle = vehicles[0]
            user = vehicle.usuario
            if not user.plazas.filter(pk=plaza.pk).exists():
                return reject(
                    "El usuario no solicitó acceso para esta plaza.",
                    user,
                    vehicle,
                )
            account_active = not user.cuenta_id or user.cuenta.is_active
            if not user.estado or not vehicle.estado or not account_active:
                return reject(
                    "El usuario o el vehículo está inactivo.",
                    user,
                    vehicle,
                )

            if RegistroUso.objects.filter(
                vehiculo=vehicle,
                hora_salida__isnull=True,
            ).exists():
                return reject(
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
                return reject(
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
                .filter(plaza=plaza, accesible=True, estado=True, activo=True)
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
                return reject(reason, user, vehicle, accreditation)

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
                plaza=plaza,
                placa_capturada=plate,
                resultado=IntentoAcceso.Resultado.AUTORIZADO,
                motivo_rechazo="",
                usuario=user,
                acreditacion=accreditation,
                vehiculo=vehicle,
                estacionamiento=space,
                registro_uso=use,
                boleto=ticket,
                fuente_captura=fuente_captura,
                confianza_ocr=confianza_ocr,
            )
            if imagen:
                attempt.imagen.save(
                    imagen.name.rsplit("/", 1)[-1], imagen, save=True
                )
                CapturaPlaca.objects.create(
                    registro_uso=use,
                    placa_detectada=plate,
                    fecha_hora=now,
                    confianza=confianza_ocr,
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
            plaza=plaza,
            fuente_captura=fuente_captura,
            confianza_ocr=confianza_ocr,
        )


def register_exit(*, operator, registro_id):
    """Cierra una entrada activa y libera el cajón en la misma transacción."""
    if not operator.is_authenticated or not operator.has_perm("registros.change_registrouso"):
        raise PermissionDenied("No tienes permiso para registrar salidas.")

    with transaction.atomic():
        use = (
            RegistroUso.objects.select_for_update()
            .select_related("estacionamiento__plaza")
            .filter(estacionamiento__plaza__in=managed_plazas(operator))
            .get(pk=registro_id)
        )
        if use.hora_salida is not None:
            raise ValidationError("El registro ya tiene una salida registrada.")
        now = timezone.localtime()
        use.hora_salida = now.time().replace(tzinfo=None)
        use.save(update_fields=("hora_salida",))

        ticket = Boleto.objects.select_for_update().filter(registro_uso=use).first()
        if ticket:
            ticket.fecha_salida = now
            ticket.save(update_fields=("fecha_salida",))

        synchronize_availability(use.estacionamiento_id)
        return use
