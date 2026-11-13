"""Provision least-privilege roles for parking managers and attendants."""

from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.db.models.signals import post_migrate
from django.dispatch import receiver


OPERATOR_PERMISSIONS = (
    ("estacionamientos", "view_operational_dashboard"),
    ("usuarios", "view_usuario"),
    ("usuarios", "change_usuario"),
    ("usuarios", "view_acreditacion"),
    ("usuarios", "change_acreditacion"),
    ("registros", "view_registrouso"),
    ("registros", "change_registrouso"),
    ("registros", "view_incidencia"),
    ("registros", "add_incidencia"),
    ("registros", "change_incidencia"),
    ("registros", "view_intentoacceso"),
)

ATTENDANT_PERMISSIONS = (
    ("registros", "validate_plate_access"),
)


@receiver(post_migrate, dispatch_uid="estacionamientos.ensure_operator_group")
def ensure_operator_group(sender, **kwargs):
    """Keep each application role limited to its current permission set."""
    role_permissions = {
        "Administrador de estacionamiento": OPERATOR_PERMISSIONS,
        "Viene viene": ATTENDANT_PERMISSIONS,
    }
    for group_name, required in role_permissions.items():
        _sync_group_permissions(group_name, required)


def _sync_group_permissions(group_name, required):
    required_permissions = Q(pk__in=[])
    for app_label, codename in required:
        required_permissions |= Q(
            content_type__app_label=app_label,
            codename=codename,
        )
    permissions = Permission.objects.filter(required_permissions)
    if permissions.count() != len(required):
        return
    group, _ = Group.objects.get_or_create(name=group_name)
    group.permissions.set(permissions)
