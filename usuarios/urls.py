from django.urls import path

from . import views


app_name = "usuarios"

urlpatterns = [
    path("registro/", views.RegistroPublicoView.as_view(), name="registro_publico"),
    path("plazas-disponibles/", views.PlazasDisponiblesView.as_view(), name="plazas_disponibles"),
    path("mi-cuenta/", views.MiCuentaView.as_view(), name="mi_cuenta"),
    path(
        "mi-cuenta/vehiculos/nuevo/",
        views.MiVehiculoCreateView.as_view(),
        name="mi_vehiculo_create",
    ),
    path(
        "acreditaciones/<int:pk>/documento/",
        views.DocumentoAcreditacionView.as_view(),
        name="acreditacion_documento",
    ),
    path("", views.UsuarioListView.as_view(), name="usuario_list"),
    path("nuevo/", views.UsuarioCreateView.as_view(), name="usuario_create"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario_update"),
    path("<int:pk>/eliminar/", views.UsuarioDeleteView.as_view(), name="usuario_delete"),

    path("vehiculos/", views.VehiculoListView.as_view(), name="vehiculo_list"),
    path("vehiculos/nuevo/", views.VehiculoCreateView.as_view(), name="vehiculo_create"),
    path("vehiculos/<str:pk>/editar/", views.VehiculoUpdateView.as_view(), name="vehiculo_update"),
    path("vehiculos/<str:pk>/eliminar/", views.VehiculoDeleteView.as_view(), name="vehiculo_delete"),

    path("acreditaciones/", views.AcreditacionListView.as_view(), name="acreditacion_list"),
    path("acreditaciones/nueva/", views.AcreditacionCreateView.as_view(), name="acreditacion_create"),
    path("acreditaciones/<int:pk>/editar/", views.AcreditacionUpdateView.as_view(), name="acreditacion_update"),
    path("acreditaciones/<int:pk>/eliminar/", views.AcreditacionDeleteView.as_view(), name="acreditacion_delete"),
]
