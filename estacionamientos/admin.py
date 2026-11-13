from django.contrib import admin
from django.contrib.auth import get_user_model

from common.admin import SuperuserOnlyModelAdmin
from .models import Estacionamiento, Plaza, Sensor
from .services import synchronize_availability


@admin.register(Plaza)
class PlazaAdmin(SuperuserOnlyModelAdmin):
    list_display = ("nombre", "estado", "municipio", "activa")
    list_filter = ("estado", "municipio", "activa")
    search_fields = ("nombre",)
    filter_horizontal = ("administradores", "personal_acceso")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "administradores":
            kwargs["queryset"] = get_user_model().objects.filter(
                is_active=True,
                is_staff=False,
                is_superuser=False,
                groups__name="Administrador de estacionamiento",
            ).distinct().order_by("username")
        elif db_field.name == "personal_acceso":
            kwargs["queryset"] = get_user_model().objects.filter(
                is_active=True,
                is_staff=False,
                is_superuser=False,
                groups__name="Viene viene",
            ).distinct().order_by("username")
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Estacionamiento)
class EstacionamientoAdmin(SuperuserOnlyModelAdmin):
    list_display = (
        "numero_cajon",
        "plaza",
        "ubicacion",
        "accesible",
        "exclusivo_discapacidad",
        "activo",
        "estado",
    )
    list_filter = ("plaza", "activo", "estado", "accesible", "exclusivo_discapacidad")
    search_fields = ("numero_cajon", "ubicacion")
    readonly_fields = ("estado",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        synchronize_availability(obj.pk)


@admin.register(Sensor)
class SensorAdmin(SuperuserOnlyModelAdmin):
    list_display = (
        "id_sensor",
        "estacionamiento",
        "tipo_sensor",
        "estado",
        "estado_ocupacion",
    )
    list_filter = ("estado", "estado_ocupacion", "tipo_sensor")
    search_fields = ("tipo_sensor", "estacionamiento__numero_cajon")
    list_select_related = ("estacionamiento",)

    def save_model(self, request, obj, form, change):
        old_space_id = None
        if change:
            old_space_id = Sensor.objects.get(pk=obj.pk).estacionamiento_id
        super().save_model(request, obj, form, change)
        for space_id in {old_space_id, obj.estacionamiento_id} - {None}:
            synchronize_availability(space_id)

    def delete_model(self, request, obj):
        space_id = obj.estacionamiento_id
        super().delete_model(request, obj)
        synchronize_availability(space_id)

    def delete_queryset(self, request, queryset):
        space_ids = set(queryset.values_list("estacionamiento_id", flat=True))
        super().delete_queryset(request, queryset)
        for space_id in space_ids:
            synchronize_availability(space_id)
