from django.urls import path

from . import views


app_name = "registros"

urlpatterns = [
    path("", views.RegistroUsoListView.as_view(), name="registro_list"),
    path("nuevo/", views.RegistroUsoCreateView.as_view(), name="registro_create"),
    path("<int:pk>/editar/", views.RegistroUsoUpdateView.as_view(), name="registro_update"),
    path("<int:pk>/eliminar/", views.RegistroUsoDeleteView.as_view(), name="registro_delete"),

    path("capturas/", views.CapturaPlacaListView.as_view(), name="captura_list"),
    path("capturas/nuevo/", views.CapturaPlacaCreateView.as_view(), name="captura_create"),
    path("capturas/<int:pk>/editar/", views.CapturaPlacaUpdateView.as_view(), name="captura_update"),
    path("capturas/<int:pk>/eliminar/", views.CapturaPlacaDeleteView.as_view(), name="captura_delete"),

    path("incidencias/", views.IncidenciaListView.as_view(), name="incidencia_list"),
    path("incidencias/nuevo/", views.IncidenciaCreateView.as_view(), name="incidencia_create"),
    path("incidencias/<int:pk>/editar/", views.IncidenciaUpdateView.as_view(), name="incidencia_update"),
    path("incidencias/<int:pk>/eliminar/", views.IncidenciaDeleteView.as_view(), name="incidencia_delete"),
]