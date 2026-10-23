from django.urls import path

from . import views


app_name = "estacionamientos"

urlpatterns = [
    path("", views.EstacionamientoListView.as_view(), name="estacionamiento_list"),
    path("nuevo/", views.EstacionamientoCreateView.as_view(), name="estacionamiento_create"),
    path("<int:pk>/editar/", views.EstacionamientoUpdateView.as_view(), name="estacionamiento_update"),
    path("<int:pk>/eliminar/", views.EstacionamientoDeleteView.as_view(), name="estacionamiento_delete"),

    path("sensores/", views.SensorListView.as_view(), name="sensor_list"),
    path("sensores/nuevo/", views.SensorCreateView.as_view(), name="sensor_create"),
    path("sensores/<int:pk>/editar/", views.SensorUpdateView.as_view(), name="sensor_update"),
    path("sensores/<int:pk>/eliminar/", views.SensorDeleteView.as_view(), name="sensor_delete"),
]