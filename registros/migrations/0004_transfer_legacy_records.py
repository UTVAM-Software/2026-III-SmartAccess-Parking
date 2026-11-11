"""Transfiere actividad legacy, preservando tablas y archivos de origen."""

import hashlib
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import migrations
from django.utils import timezone


LOCAL_TIME_ZONE = ZoneInfo("America/Mexico_City")
LEGACY_TIME_ZONE = ZoneInfo("UTC")


def _normalized(value):
    return (value or "").strip().casefold()


def _legacy_instant(value):
    """Interpreta los timestamps SQLite legacy según la zona histórica UTC."""
    if value is None:
        return None
    return value.replace(tzinfo=LEGACY_TIME_ZONE)


def _file_digest(storage, name):
    digest = hashlib.sha256()
    with storage.open(name, "rb") as image_file:
        for chunk in iter(lambda: image_file.read(65536), b""):
            digest.update(chunk)
    return digest.digest()


def _copy_image(source_storage, target_storage, name, entity, legacy_pk):
    if not name:
        return
    if not source_storage.exists(name):
        raise RuntimeError(
            f"Falta el archivo de imagen de {entity} legacy id={legacy_pk}; "
            "se detuvo la migración sin borrar el registro."
        )
    if target_storage.exists(name):
        if _file_digest(source_storage, name) != _file_digest(target_storage, name):
            raise RuntimeError(
                f"Colisión de imagen al migrar {entity} legacy id={legacy_pk}."
            )
        return
    with source_storage.open(name, "rb") as image_file:
        target_storage.save(name, image_file)


def transfer_legacy_records(apps, schema_editor):
    """Migra boletos, usos, pagos y capturas tras validar sus relaciones."""
    using = schema_editor.connection.alias
    LegacyUser = apps.get_model("parking", "Usuario")
    LegacyVehicle = apps.get_model("parking", "Vehiculo")
    LegacyStall = apps.get_model("parking", "Estacionamiento")
    LegacyTicket = apps.get_model("parking", "Boleto")
    LegacyUse = apps.get_model("parking", "RegistroUso")
    LegacyCapture = apps.get_model("parking", "CapturaPlaca")
    LegacyPayment = apps.get_model("parking", "Pago")
    User = apps.get_model("usuarios", "Usuario")
    Vehicle = apps.get_model("usuarios", "Vehiculo")
    Stall = apps.get_model("estacionamientos", "Estacionamiento")
    Ticket = apps.get_model("registros", "Boleto")
    Use = apps.get_model("registros", "RegistroUso")
    Capture = apps.get_model("registros", "CapturaPlaca")
    Payment = apps.get_model("registros", "Pago")

    legacy_users = list(LegacyUser.objects.using(using).all())
    legacy_vehicles = list(LegacyVehicle.objects.using(using).all())
    legacy_stalls = list(LegacyStall.objects.using(using).all())
    legacy_tickets = list(LegacyTicket.objects.using(using).all())
    legacy_uses = list(LegacyUse.objects.using(using).all())
    legacy_captures = list(LegacyCapture.objects.using(using).all())
    legacy_payments = list(LegacyPayment.objects.using(using).all())

    users = list(User.objects.using(using).all())
    user_map = {}
    for legacy in legacy_users:
        matches = [
            user for user in users
            if _normalized(user.correo_electronico) == _normalized(legacy.correo)
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"El usuario legacy id={legacy.pk} tiene {len(matches)} "
                "correspondencias canónicas; no se asignó arbitrariamente."
            )
        user_map[legacy.pk] = matches[0]

    vehicles = list(Vehicle.objects.using(using).all())
    vehicle_map = {}
    for legacy in legacy_vehicles:
        matches = [
            vehicle for vehicle in vehicles
            if _normalized(vehicle.placa) == _normalized(legacy.placa)
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"El vehículo legacy id={legacy.pk} tiene {len(matches)} "
                "correspondencias canónicas."
            )
        vehicle = matches[0]
        owner = user_map.get(legacy.usuario_id)
        if owner is None or vehicle.usuario_id != owner.pk:
            raise RuntimeError(
                f"La relación de propietario del vehículo legacy "
                f"id={legacy.pk} no coincide."
            )
        vehicle_map[legacy.pk] = vehicle

    stalls = list(Stall.objects.using(using).all())
    stall_map = {}
    for legacy in legacy_stalls:
        matches = [
            stall for stall in stalls
            if _normalized(stall.numero_cajon) == _normalized(legacy.numero)
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"El cajón legacy id={legacy.pk} tiene {len(matches)} "
                "correspondencias canónicas."
            )
        stall_map[legacy.pk] = matches[0]

    tickets = {ticket.pk: ticket for ticket in legacy_tickets}
    uses_per_ticket = {}
    active_uses_per_stall = {}
    use_map = {}
    for legacy in legacy_uses:
        if not legacy.autorizado:
            raise RuntimeError(
                f"El uso legacy id={legacy.pk} está marcado como rechazado y no "
                "tiene operador registrado; no se convertirá en RegistroUso/Boleto."
            )
        if legacy.boleto_id not in tickets:
            raise RuntimeError(
                f"El uso legacy id={legacy.pk} referencia un boleto inexistente."
            )
        if legacy.estacionamiento_id not in stall_map:
            raise RuntimeError(
                f"El uso legacy id={legacy.pk} referencia un cajón sin mapa."
            )
        uses_per_ticket[legacy.boleto_id] = (
            uses_per_ticket.get(legacy.boleto_id, 0) + 1
        )
        use_map[legacy.pk] = None
        if legacy.fecha_salida is None:
            stall_pk = stall_map[legacy.estacionamiento_id].pk
            active_uses_per_stall[stall_pk] = active_uses_per_stall.get(stall_pk, 0) + 1

    multiply_used_tickets = [pk for pk, count in uses_per_ticket.items() if count > 1]
    if multiply_used_tickets:
        raise RuntimeError(
            "Hay boletos legacy asociados a varios usos; la relación no se puede "
            "reducir a un boleto por entrada sin conciliación manual."
        )

    current_active = {}
    for use in Use.objects.using(using).filter(hora_salida__isnull=True):
        current_active[use.estacionamiento_id] = current_active.get(use.estacionamiento_id, 0) + 1
    for stall_pk, count in active_uses_per_stall.items():
        if count + current_active.get(stall_pk, 0) > 1:
            raise RuntimeError(
                f"Hay usos activos incompatibles para estacionamiento id={stall_pk}."
            )

    def usage_key(vehicle_id, stall_id, entry):
        if timezone.is_aware(entry):
            entry = entry.astimezone(LOCAL_TIME_ZONE)
        return (
            vehicle_id,
            stall_id,
            entry.date(),
            entry.time().replace(tzinfo=None),
        )

    existing_usage_keys = set()
    for current in Use.objects.using(using).all():
        key = usage_key(
            current.vehiculo_id,
            current.estacionamiento_id,
            timezone.make_aware(
                timezone.datetime.combine(current.fecha, current.hora_entrada),
                LOCAL_TIME_ZONE,
            ),
        )
        if key in existing_usage_keys:
            raise RuntimeError(
                "Hay registros canónicos duplicados en la clave vehículo/cajón/entrada."
            )
        existing_usage_keys.add(key)

    seen_legacy_usage_keys = set()
    for legacy in legacy_uses:
        vehicle = vehicle_map[tickets[legacy.boleto_id].vehiculo_id]
        stall = stall_map[legacy.estacionamiento_id]
        legacy_entry = _legacy_instant(legacy.fecha_entrada).astimezone(LOCAL_TIME_ZONE)
        key = usage_key(vehicle.pk, stall.pk, legacy_entry)
        if key in existing_usage_keys or key in seen_legacy_usage_keys:
            raise RuntimeError(
                f"El uso legacy id={legacy.pk} coincide con otra entrada existente; "
                "requiere conciliación manual."
            )
        seen_legacy_usage_keys.add(key)

    legacy_ticket_numbers = [_normalized(ticket.numero_boleto) for ticket in legacy_tickets]
    if len(set(legacy_ticket_numbers)) != len(legacy_ticket_numbers):
        raise RuntimeError("Hay números de boleto legacy duplicados tras normalizarlos.")
    if Ticket.objects.using(using).exists() or Payment.objects.using(using).exists():
        raise RuntimeError(
            "Ya existen boletos o pagos canónicos antes de importar el archivo legacy."
        )

    legacy_use_ids = {use.pk for use in legacy_uses}
    for capture in legacy_captures:
        if capture.registro_uso_id not in legacy_use_ids:
            raise RuntimeError(
                f"Captura legacy id={capture.pk} sin registro de uso correspondiente."
            )
    legacy_ticket_ids = {ticket.pk for ticket in legacy_tickets}
    for payment in legacy_payments:
        if payment.boleto_id not in legacy_ticket_ids:
            raise RuntimeError(
                f"Pago legacy id={payment.pk} sin boleto correspondiente."
            )

    source_storage = FileSystemStorage(location=settings.MEDIA_ROOT)
    target_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)
    for capture in Capture.objects.using(using).exclude(imagen=""):
        _copy_image(
            source_storage,
            target_storage,
            capture.imagen.name,
            "captura canónica",
            capture.pk,
        )
    for capture in legacy_captures:
        _copy_image(
            source_storage,
            target_storage,
            capture.imagen.name,
            "captura",
            capture.pk,
        )

    ticket_map = {}
    for legacy in legacy_tickets:
        vehicle = vehicle_map.get(legacy.vehiculo_id)
        if vehicle is None:
            raise RuntimeError(
                f"El boleto legacy id={legacy.pk} referencia un vehículo sin mapa."
            )
        ticket = Ticket.objects.using(using).create(
            vehiculo_id=vehicle.pk,
            numero_boleto=legacy.numero_boleto,
            fecha_entrada=_legacy_instant(legacy.fecha_entrada),
            fecha_salida=_legacy_instant(legacy.fecha_salida),
            monto=legacy.monto,
            cargo_adicional=legacy.cargo_adicional,
            pagado=legacy.pagado,
        )
        ticket_map[legacy.pk] = ticket

    for legacy in legacy_uses:
        ticket = ticket_map[legacy.boleto_id]
        vehicle = vehicle_map[tickets[legacy.boleto_id].vehiculo_id]
        stall = stall_map[legacy.estacionamiento_id]
        entry = _legacy_instant(legacy.fecha_entrada).astimezone(LOCAL_TIME_ZONE)
        exit_time = _legacy_instant(legacy.fecha_salida)
        if exit_time:
            exit_time = exit_time.astimezone(LOCAL_TIME_ZONE)
        use = Use.objects.using(using).create(
            vehiculo_id=vehicle.pk,
            estacionamiento_id=stall.pk,
            fecha=entry.date(),
            hora_entrada=entry.time().replace(tzinfo=None),
            hora_salida=(exit_time.time().replace(tzinfo=None) if exit_time else None),
            estado_acreditacion=("Autorizado" if legacy.autorizado else "No autorizado"),
            autorizado=legacy.autorizado,
        )
        ticket.registro_uso_id = use.pk
        ticket.save(using=using, update_fields=("registro_uso",))
        use_map[legacy.pk] = use
        if exit_time is None and stall.estado:
            stall.estado = False
            stall.save(using=using, update_fields=("estado",))

    for legacy in legacy_captures:
        use = use_map[legacy.registro_uso_id]
        Capture.objects.using(using).create(
            registro_uso_id=use.pk,
            placa_detectada=legacy.placa_detectada,
            fecha_hora=_legacy_instant(legacy.fecha_captura),
            confianza=legacy.confianza,
            imagen=legacy.imagen,
        )

    for legacy in legacy_payments:
        ticket = ticket_map[legacy.boleto_id]
        Payment.objects.using(using).create(
            boleto_id=ticket.pk,
            fecha_pago=_legacy_instant(legacy.fecha_pago),
            monto_pagado=legacy.monto_pagado,
            metodo_pago=legacy.metodo_pago,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("estacionamientos", "0003_transfer_legacy_stalls"),
        ("parking", "0001_initial"),
        ("registros", "0003_capturaplaca_confianza"),
        ("usuarios", "0003_transfer_legacy_people"),
    ]

    operations = [
        migrations.RunPython(
            transfer_legacy_records,
            reverse_code=migrations.RunPython.noop,
        ),
    ]