from django.contrib import messages
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CapturaPlacaForm, IncidenciaForm, RegistroUsoForm
from .models import CapturaPlaca, Incidencia, RegistroUso


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


class RegistroUsoListView(ListView):
    model = RegistroUso
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Registros de uso",
        "create_url": "registros:registro_create",
        "update_url": "registros:registro_update",
        "delete_url": "registros:registro_delete",
    }


class RegistroUsoCreateView(CreateView):
    model = RegistroUso
    form_class = RegistroUsoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:registro_list")
    extra_context = {"title": "Crear registro de uso"}


class RegistroUsoUpdateView(UpdateView):
    model = RegistroUso
    form_class = RegistroUsoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:registro_list")
    extra_context = {"title": "Editar registro de uso"}


class RegistroUsoDeleteView(EliminacionProtegidaView):
    model = RegistroUso
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:registro_list")
    extra_context = {"title": "registro de uso"}


class CapturaPlacaListView(ListView):
    model = CapturaPlaca
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Capturas de placa",
        "create_url": "registros:captura_create",
        "update_url": "registros:captura_update",
        "delete_url": "registros:captura_delete",
    }


class CapturaPlacaCreateView(CreateView):
    model = CapturaPlaca
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    extra_context = {"title": "Crear captura de placa"}


class CapturaPlacaUpdateView(UpdateView):
    model = CapturaPlaca
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    extra_context = {"title": "Editar captura de placa"}


class CapturaPlacaDeleteView(EliminacionProtegidaView):
    model = CapturaPlaca
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:captura_list")
    extra_context = {"title": "captura de placa"}


class IncidenciaListView(ListView):
    model = Incidencia
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Incidencias",
        "create_url": "registros:incidencia_create",
        "update_url": "registros:incidencia_update",
        "delete_url": "registros:incidencia_delete",
    }


class IncidenciaCreateView(CreateView):
    model = Incidencia
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    extra_context = {"title": "Crear incidencia"}


class IncidenciaUpdateView(UpdateView):
    model = Incidencia
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    extra_context = {"title": "Editar incidencia"}


class IncidenciaDeleteView(EliminacionProtegidaView):
    model = Incidencia
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:incidencia_list")
    extra_context = {"title": "incidencia"}