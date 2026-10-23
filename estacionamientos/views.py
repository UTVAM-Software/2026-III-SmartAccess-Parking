from django.contrib import messages
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import EstacionamientoForm, SensorForm
from .models import Estacionamiento, Sensor


class EliminacionProtegidaView(DeleteView):
    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar porque hay registros relacionados.",
            )
        else:
            messages.success(self.request, "Registro eliminado correctamente.")

        return HttpResponseRedirect(self.get_success_url())


class EstacionamientoListView(ListView):
    model = Estacionamiento
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Estacionamientos",
        "create_url": "estacionamientos:estacionamiento_create",
        "update_url": "estacionamientos:estacionamiento_update",
        "delete_url": "estacionamientos:estacionamiento_delete",
    }


class EstacionamientoCreateView(CreateView):
    model = Estacionamiento
    form_class = EstacionamientoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "Crear estacionamiento"}


class EstacionamientoUpdateView(UpdateView):
    model = Estacionamiento
    form_class = EstacionamientoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "Editar estacionamiento"}


class EstacionamientoDeleteView(EliminacionProtegidaView):
    model = Estacionamiento
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "estacionamiento"}


class SensorListView(ListView):
    model = Sensor
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Sensores",
        "create_url": "estacionamientos:sensor_create",
        "update_url": "estacionamientos:sensor_update",
        "delete_url": "estacionamientos:sensor_delete",
    }


class SensorCreateView(CreateView):
    model = Sensor
    form_class = SensorForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "Crear sensor"}


class SensorUpdateView(UpdateView):
    model = Sensor
    form_class = SensorForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "Editar sensor"}


class SensorDeleteView(EliminacionProtegidaView):
    model = Sensor
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "sensor"}