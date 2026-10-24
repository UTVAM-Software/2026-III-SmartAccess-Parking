from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CapturaPlacaForm, IncidenciaForm, RegistroUsoForm
from .models import CapturaPlaca, Incidencia, RegistroUso


class AccesoRegistrosMixin(LoginRequiredMixin, PermissionRequiredMixin):
    login_url = reverse_lazy("admin:login")


class EliminacionProtegidaView(DeleteView):
    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar porque existen registros relacionados que lo protegen.",
            )
        else:
            messages.success(self.request, "Registro eliminado correctamente.")

        return HttpResponseRedirect(self.get_success_url())


class RegistroUsoListView(AccesoRegistrosMixin, ListView):
    model = RegistroUso
    permission_required = "registros.view_registrouso"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Registros de uso",
        "create_url": "registros:registro_create",
        "update_url": "registros:registro_update",
        "delete_url": "registros:registro_delete",
    }


class RegistroUsoCreateView(AccesoRegistrosMixin, SuccessMessageMixin, CreateView):
    model = RegistroUso
    permission_required = "registros.add_registrouso"
    form_class = RegistroUsoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:registro_list")
    success_message = "Registro de uso creado correctamente."
    extra_context = {"title": "Crear registro de uso"}


class RegistroUsoUpdateView(AccesoRegistrosMixin, SuccessMessageMixin, UpdateView):
    model = RegistroUso
    permission_required = "registros.change_registrouso"
    form_class = RegistroUsoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:registro_list")
    success_message = "Registro de uso actualizado correctamente."
    extra_context = {"title": "Editar registro de uso"}


class RegistroUsoDeleteView(AccesoRegistrosMixin, EliminacionProtegidaView):
    model = RegistroUso
    permission_required = "registros.delete_registrouso"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:registro_list")
    extra_context = {"title": "registro de uso"}


class CapturaPlacaListView(AccesoRegistrosMixin, ListView):
    model = CapturaPlaca
    permission_required = "registros.view_capturaplaca"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Capturas de placa",
        "create_url": "registros:captura_create",
        "update_url": "registros:captura_update",
        "delete_url": "registros:captura_delete",
    }


class CapturaPlacaCreateView(AccesoRegistrosMixin, SuccessMessageMixin, CreateView):
    model = CapturaPlaca
    permission_required = "registros.add_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa creada correctamente."
    extra_context = {"title": "Crear captura de placa"}


class CapturaPlacaUpdateView(AccesoRegistrosMixin, SuccessMessageMixin, UpdateView):
    model = CapturaPlaca
    permission_required = "registros.change_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa actualizada correctamente."
    extra_context = {"title": "Editar captura de placa"}


class CapturaPlacaDeleteView(AccesoRegistrosMixin, EliminacionProtegidaView):
    model = CapturaPlaca
    permission_required = "registros.delete_capturaplaca"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:captura_list")
    extra_context = {"title": "captura de placa"}


class IncidenciaListView(AccesoRegistrosMixin, ListView):
    model = Incidencia
    permission_required = "registros.view_incidencia"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Incidencias",
        "create_url": "registros:incidencia_create",
        "update_url": "registros:incidencia_update",
        "delete_url": "registros:incidencia_delete",
    }


class IncidenciaCreateView(AccesoRegistrosMixin, SuccessMessageMixin, CreateView):
    model = Incidencia
    permission_required = "registros.add_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia creada correctamente."
    extra_context = {"title": "Crear incidencia"}


class IncidenciaUpdateView(AccesoRegistrosMixin, SuccessMessageMixin, UpdateView):
    model = Incidencia
    permission_required = "registros.change_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia actualizada correctamente."
    extra_context = {"title": "Editar incidencia"}


class IncidenciaDeleteView(AccesoRegistrosMixin, EliminacionProtegidaView):
    model = Incidencia
    permission_required = "registros.delete_incidencia"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:incidencia_list")
    extra_context = {"title": "incidencia"}