"""Transfiere cajones legacy y conserva intactas las tablas de parking."""

from django.db import migrations


def transfer_legacy_stalls(apps, schema_editor):
    """Migra cajones con coincidencias únicas y estado verificable."""
    using = schema_editor.connection.alias
    CurrentStall = apps.get_model("estacionamientos", "Estacionamiento")
    LegacyStall = apps.get_model("parking", "Estacionamiento")
    LegacyUse = apps.get_model("parking", "RegistroUso")

    def normalized(value):
        return (value or "").strip().casefold()

    active_uses = {}
    for use in LegacyUse.objects.using(using).filter(fecha_salida__isnull=True):
        active_uses[use.estacionamiento_id] = (
            active_uses.get(use.estacionamiento_id, 0) + 1
        )
    duplicated_active = [pk for pk, count in active_uses.items() if count > 1]
    if duplicated_active:
        raise RuntimeError(
            "Hay más de un uso activo para un mismo cajón legacy; "
            "requiere conciliación antes de migrar."
        )

    current_stalls = list(CurrentStall.objects.using(using).all())
    for legacy in LegacyStall.objects.using(using).order_by("pk"):
        key = normalized(legacy.numero)
        matches = [
            stall for stall in current_stalls
            if normalized(stall.numero_cajon) == key
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"Correspondencia ambigua para cajón legacy id={legacy.pk}."
            )

        has_active_use = active_uses.get(legacy.pk, 0) > 0
        expected_available = bool(legacy.activo) and not has_active_use
        if matches:
            stall = matches[0]
            if stall.ubicacion and legacy.ubicacion and stall.ubicacion != legacy.ubicacion:
                raise RuntimeError(
                    f"Ubicación conflictiva para cajón legacy id={legacy.pk}."
                )
            if stall.accesible != legacy.accesible or stall.activo != legacy.activo:
                raise RuntimeError(
                    f"Atributos conflictivos para cajón legacy id={legacy.pk}."
                )
            if stall.ubicacion != legacy.ubicacion and not stall.ubicacion:
                stall.ubicacion = legacy.ubicacion
                stall.save(using=using, update_fields=("ubicacion",))
            if has_active_use:
                stall.estado = False
                stall.save(using=using, update_fields=("estado",))
            continue

        stall = CurrentStall.objects.using(using).create(
            numero_cajon=legacy.numero,
            ubicacion=legacy.ubicacion,
            accesible=legacy.accesible,
            exclusivo_discapacidad=False,
            activo=legacy.activo,
            estado=expected_available,
        )
        current_stalls.append(stall)


class Migration(migrations.Migration):
    dependencies = [
        ("estacionamientos", "0002_estacionamiento_accesible_estacionamiento_activo_and_more"),
        ("parking", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            transfer_legacy_stalls,
            reverse_code=migrations.RunPython.noop,
        ),
    ]