"""Administración de perfiles, vehículos y acreditaciones."""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from common.admin import SuperuserOnlyModelAdmin
from .forms import VehiculoForm
from .models import Acreditacion, Usuario, Vehiculo


@admin.register(Usuario)
class UsuarioAdmin(SuperuserOnlyModelAdmin):
    list_display = (
        "id_usuario",
        "cuenta",
        "nombre",
        "correo_electronico",
        "telefono",
        "estado",
    )
    list_filter = ("estado",)
    search_fields = (
        "cuenta__username",
        "nombre",
        "correo_electronico",
        "telefono",
    )


@admin.register(Vehiculo)
class VehiculoAdmin(SuperuserOnlyModelAdmin):
    form = VehiculoForm
    list_display = ("placa", "usuario", "marca", "modelo", "estado")
    list_filter = ("estado", "marca")
    search_fields = ("placa", "usuario__nombre", "usuario__correo_electronico")
    list_select_related = ("usuario",)


@admin.register(Acreditacion)
class AcreditacionAdmin(SuperuserOnlyModelAdmin):
    list_display = (
        "id",
        "usuario",
        "tipo",
        "fecha_validacion",
        "fecha_vencimiento",
        "estado",
        "documento_privado",
    )
    list_filter = ("tipo", "estado")
    search_fields = ("usuario__nombre", "usuario__correo_electronico", "documento")
    list_select_related = ("usuario",)
    exclude = ("documento_imagen",)
    readonly_fields = ("documento_privado",)

    @admin.display(description="Documento")
    def documento_privado(self, obj):
        if not obj.documento_imagen:
            return obj.documento or "Sin documento"
        return format_html(
            '<a href="{}">Ver documento privado</a>',
            reverse("usuarios:acreditacion_documento", args=[obj.pk]),
        )
