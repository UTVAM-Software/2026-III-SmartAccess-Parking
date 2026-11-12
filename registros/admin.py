"""Configuración de administración para los modelos de registros."""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Boleto, CapturaPlaca, Incidencia, IntentoAcceso, Pago, RegistroUso


@admin.register(RegistroUso)
class RegistroUsoAdmin(admin.ModelAdmin):
    """Administra registros de uso con permisos estándar de Django."""

    list_display = ("id_registro", "vehiculo", "estacionamiento",
                    "fecha", "hora_entrada", "hora_salida", "estado_acreditacion")
    list_filter = ("estado_acreditacion", "fecha")
    search_fields = ("vehiculo__placa", "estado_acreditacion")
    list_select_related = ("vehiculo", "estacionamiento")


@admin.register(CapturaPlaca)
class CapturaPlacaAdmin(admin.ModelAdmin):
    """Administra capturas de placa y su evidencia."""

    list_display = (
        "id_captura",
        "registro_uso",
        "placa_detectada",
        "fecha_hora",
        "imagen_privada",
    )
    search_fields = ("placa_detectada", "registro_uso__vehiculo__placa")
    list_select_related = ("registro_uso", "registro_uso__vehiculo")

    @admin.display(description="Evidencia")
    def imagen_privada(self, obj):
        """Enlaza a la vista que aplica permisos en lugar de exponer MEDIA_URL."""
        if not obj.imagen:
            return "Sin imagen"
        return format_html(
            '<a href="{}">Ver imagen</a>',
            reverse("registros:captura_imagen", args=[obj.pk]),
        )


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    """Administra incidencias según los permisos estándar de Django."""

    list_display = ("id_incidencia", "registro_uso",
                    "tipo", "fecha_hora", "estado")
    list_filter = ("tipo", "estado", "fecha_hora")
    search_fields = ("tipo", "descripcion", "registro_uso__vehiculo__placa")
    list_select_related = ("registro_uso", "registro_uso__vehiculo")


@admin.register(Boleto)
class BoletoAdmin(admin.ModelAdmin):
    """Consulta boletos; su creación ocurre solo en el flujo de acceso."""

    list_display = ("numero_boleto", "vehiculo", "registro_uso", "fecha_entrada", "fecha_salida", "pagado")
    search_fields = ("numero_boleto", "vehiculo__placa")
    list_select_related = ("vehiculo", "registro_uso")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """Permite consultar únicamente pagos históricos sin operar cobros."""

    list_display = ("boleto", "fecha_pago", "monto_pagado", "metodo_pago")
    readonly_fields = ("boleto", "fecha_pago", "monto_pagado", "metodo_pago")
    list_select_related = ("boleto",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IntentoAcceso)
class IntentoAccesoAdmin(admin.ModelAdmin):
    """Consulta el historial inmutable de decisiones de acceso."""

    list_display = (
        "id_intento",
        "fecha_hora",
        "placa_capturada",
        "resultado",
        "operador",
        "acreditacion",
        "imagen_privada",
    )
    list_filter = ("resultado", "fuente_captura", "fecha_hora")
    search_fields = ("placa_capturada", "motivo_rechazo", "operador__username")
    list_select_related = (
        "operador",
        "usuario",
        "acreditacion",
        "vehiculo",
        "estacionamiento",
    )

    @admin.display(description="Fotografía")
    def imagen_privada(self, obj):
        """Enlaza a la vista protegida de la fotografía."""
        if not obj.imagen:
            return "Sin imagen"
        return format_html(
            '<a href="{}">Ver imagen</a>',
            reverse("registros:intento_imagen", args=[obj.pk]),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
