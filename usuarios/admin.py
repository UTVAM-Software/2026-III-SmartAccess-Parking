"""Configuración de administración de usuarios y acreditaciones."""

from django.contrib import admin

from .models import Acreditacion, Usuario, Vehiculo


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
	"""Administra perfiles canónicos."""

	list_display = ("id_usuario", "nombre", "correo_electronico", "telefono", "estado")
	search_fields = ("nombre", "correo_electronico", "telefono")


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
	"""Administra vehículos y sus propietarios canónicos."""

	list_display = ("placa", "usuario", "marca", "modelo", "estado")
	search_fields = ("placa", "usuario__nombre", "usuario__correo_electronico")
	list_select_related = ("usuario",)


@admin.register(Acreditacion)
class AcreditacionAdmin(admin.ModelAdmin):
	"""Administra acreditaciones, aprobación y fecha de vencimiento."""

	list_display = (
		"id",
		"usuario",
		"tipo",
		"fecha_validacion",
		"fecha_vencimiento",
		"estado",
	)
	list_filter = ("tipo", "estado")
	search_fields = ("usuario__nombre", "usuario__correo_electronico", "documento")
	list_select_related = ("usuario",)
