"""Transfiere perfiles y acreditaciones legacy sin borrar las tablas fuente."""

from django.db import migrations


def _normalized(value):
    return (value or "").strip().casefold()


def _assert_same(entity, legacy_pk, field, current_value, legacy_value):
    if current_value not in (None, "") and legacy_value not in (None, ""):
        if current_value != legacy_value:
            raise RuntimeError(
                f"Conflicto en {entity} legacy id={legacy_pk}, campo {field}. "
                "Se conserva el origen; requiere conciliación manual."
            )


def transfer_legacy_people(apps, schema_editor):
    """Migra datos legacy sin borrar filas ni reinterpretar categorías."""
    using = schema_editor.connection.alias
    LegacyUser = apps.get_model("parking", "Usuario")
    LegacyVehicle = apps.get_model("parking", "Vehiculo")
    LegacyAccreditation = apps.get_model("parking", "Acreditacion")
    User = apps.get_model("usuarios", "Usuario")
    Vehicle = apps.get_model("usuarios", "Vehiculo")
    Accreditation = apps.get_model("usuarios", "Acreditacion")

    users = list(User.objects.using(using).all())
    user_map = {}
    for legacy in LegacyUser.objects.using(using).order_by("pk"):
        email = _normalized(legacy.correo)
        if not email:
            raise RuntimeError(
                f"Usuario legacy id={legacy.pk} no tiene correo para vincular."
            )
        matches = [user for user in users if _normalized(user.correo_electronico) == email]
        if len(matches) > 1:
            raise RuntimeError(
                f"Correo ambiguo para usuario legacy id={legacy.pk}; "
                "requiere conciliación manual."
            )

        if matches:
            user = matches[0]
            for field in ("nombre", "telefono", "apellido_paterno", "apellido_materno"):
                _assert_same(
                    "usuario",
                    legacy.pk,
                    field,
                    getattr(user, field),
                    getattr(legacy, field, "") or "",
                )
            _assert_same(
                "usuario",
                legacy.pk,
                "fecha_registro",
                user.fecha_registro,
                legacy.fecha_registro,
            )
            changed = []
            for field in ("apellido_paterno", "apellido_materno"):
                if not getattr(user, field) and getattr(legacy, field):
                    setattr(user, field, getattr(legacy, field))
                    changed.append(field)
            if not user.fecha_registro and legacy.fecha_registro:
                user.fecha_registro = legacy.fecha_registro
                changed.append("fecha_registro")
            if changed:
                user.save(using=using, update_fields=changed)
        else:
            user = User.objects.using(using).create(
                nombre=legacy.nombre,
                apellido_paterno=legacy.apellido_paterno,
                apellido_materno=legacy.apellido_materno,
                correo_electronico=legacy.correo,
                telefono=legacy.telefono,
                fecha_registro=legacy.fecha_registro,
                estado=True,
            )
            users.append(user)
        user_map[legacy.pk] = user

    vehicles = list(Vehicle.objects.using(using).all())
    vehicle_map = {}
    for legacy in LegacyVehicle.objects.using(using).order_by("pk"):
        plate = (legacy.placa or "").strip()
        if not plate or len(plate) > 15:
            raise RuntimeError(
                f"Placa no representable en vehículo legacy id={legacy.pk}; "
                "requiere conciliación antes de migrar."
            )
        owner = user_map.get(legacy.usuario_id)
        if owner is None:
            raise RuntimeError(
                f"Propietario sin correspondencia para vehículo legacy id={legacy.pk}."
            )
        matches = [
            vehicle for vehicle in vehicles
            if _normalized(vehicle.placa) == _normalized(plate)
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"Placa ambigua para vehículo legacy id={legacy.pk}; "
                "requiere conciliación manual."
            )

        if matches:
            vehicle = matches[0]
            if vehicle.usuario_id != owner.pk:
                raise RuntimeError(
                    f"Propietario distinto para vehículo legacy id={legacy.pk}."
                )
            for field in ("modelo", "marca", "color"):
                _assert_same(
                    "vehículo",
                    legacy.pk,
                    field,
                    getattr(vehicle, field),
                    getattr(legacy, field, "") or "",
                )
            changed = []
            for field in ("marca", "color"):
                if not getattr(vehicle, field) and getattr(legacy, field):
                    setattr(vehicle, field, getattr(legacy, field))
                    changed.append(field)
            if changed:
                vehicle.save(using=using, update_fields=changed)
        else:
            vehicle = Vehicle.objects.using(using).create(
                placa=plate,
                usuario_id=owner.pk,
                modelo=legacy.modelo,
                marca=legacy.marca,
                color=legacy.color,
                estado=True,
            )
            vehicles.append(vehicle)
        vehicle_map[legacy.pk] = vehicle

    existing_accreditations = {
        accreditation.usuario_id: accreditation
        for accreditation in Accreditation.objects.using(using).all()
    }
    for legacy in LegacyAccreditation.objects.using(using).order_by("pk"):
        if (legacy.tipo or "").strip().upper() != "DISCAPACIDAD":
            raise RuntimeError(
                f"Tipo no clasificable en acreditación legacy id={legacy.pk}; "
                "solo se admite DISCAPACIDAD y requiere revisión manual."
            )
        user = user_map.get(legacy.usuario_id)
        if user is None:
            raise RuntimeError(
                f"Usuario sin correspondencia para acreditación legacy id={legacy.pk}."
            )
        current = existing_accreditations.get(user.pk)
        values = {
            "tipo": "DISCAPACIDAD",
            "documento": legacy.documento,
            "fecha_validacion": legacy.fecha_validacion,
            "fecha_vencimiento": None,
            "estado": legacy.estado,
        }
        if current:
            for field, value in values.items():
                if getattr(current, field) != value:
                    raise RuntimeError(
                        f"Acreditación duplicada/conflictiva para usuario legacy "
                        f"id={legacy.usuario_id}; requiere conciliación manual."
                    )
        else:
            accreditation = Accreditation.objects.using(using).create(
                usuario_id=user.pk,
                **values,
            )
            existing_accreditations[user.pk] = accreditation


class Migration(migrations.Migration):
    dependencies = [
        ("parking", "0001_initial"),
        ("usuarios", "0002_usuario_apellido_materno_usuario_apellido_paterno_and_more"),
    ]

    operations = [
        migrations.RunPython(
            transfer_legacy_people,
            reverse_code=migrations.RunPython.noop,
        ),
    ]