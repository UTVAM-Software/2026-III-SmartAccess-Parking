from django.urls import path

from . import views


app_name = "usuarios"

urlpatterns = [
    path("", views.UsuarioListView.as_view(), name="usuario_list"),
    path("nuevo/", views.UsuarioCreateView.as_view(), name="usuario_create"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario_update"),
    path("<int:pk>/eliminar/", views.UsuarioDeleteView.as_view(), name="usuario_delete"),

    path("vehiculos/", views.VehiculoListView.as_view(), name="vehiculo_list"),
    path("vehiculos/nuevo/", views.VehiculoCreateView.as_view(), name="vehiculo_create"),
    path("vehiculos/<str:pk>/editar/", views.VehiculoUpdateView.as_view(), name="vehiculo_update"),
    path("vehiculos/<str:pk>/eliminar/", views.VehiculoDeleteView.as_view(), name="vehiculo_delete"),
]