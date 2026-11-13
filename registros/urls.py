"""Rutas del módulo Registros e Incidencias."""

from django.urls import path

from . import views


app_name = "registros"

# Cada vista comprueba autenticación y el permiso del modelo, incluso al acceder por URL directa.
urlpatterns = [
    # CRUD de registros de uso.
    path("", views.RegistroUsoListView.as_view(), name="registro_list"),
    path("nuevo/", views.RegistroUsoCreateView.as_view(), name="registro_create"),
    path("<int:pk>/editar/", views.RegistroUsoUpdateView.as_view(), name="registro_update"),
    path("<int:pk>/eliminar/", views.RegistroUsoDeleteView.as_view(), name="registro_delete"),

    # CRUD de capturas de placa.
    path("capturas/", views.CapturaPlacaListView.as_view(), name="captura_list"),
    path("capturas/nuevo/", views.CapturaPlacaCreateView.as_view(), name="captura_create"),
    path("capturas/<int:pk>/editar/", views.CapturaPlacaUpdateView.as_view(), name="captura_update"),
    path("capturas/<int:pk>/eliminar/", views.CapturaPlacaDeleteView.as_view(), name="captura_delete"),

    # CRUD de incidencias.
    path("incidencias/", views.IncidenciaListView.as_view(), name="incidencia_list"),
    path("incidencias/nuevo/", views.IncidenciaCreateView.as_view(), name="incidencia_create"),
    path("incidencias/<int:pk>/editar/", views.IncidenciaUpdateView.as_view(), name="incidencia_update"),
    path("incidencias/<int:pk>/eliminar/", views.IncidenciaDeleteView.as_view(), name="incidencia_delete"),

    # El operador valida la placa manualmente o confirma la propuesta de OCR.
    path("intentos/", views.IntentoAccesoListView.as_view(), name="intento_list"),
    path("intentos/nuevo/", views.IntentoAccesoCreateView.as_view(), name="intento_create"),
    path("intentos/<int:pk>/imagen/", views.IntentoAccesoImagenView.as_view(), name="intento_imagen"),
    path("capturas/<int:pk>/imagen/", views.CapturaPlacaImagenView.as_view(), name="captura_imagen"),

    # Solo POST puede cerrar una entrada activa.
    path("uso/<int:pk>/salida/", views.RegistroSalidaView.as_view(), name="registro_salida"),
]
