from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import EstacionamientoForm, SensorForm
from .models import Estacionamiento, Sensor


class AccesoEstacionamientosMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Exige autenticación y permisos CRUD para cajones y sensores."""

    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        """Expone permisos de CRUD para controlar las acciones de lista."""
        context = super().get_context_data(**kwargs)
        options = self.model._meta
        for action in ("add", "change", "delete"):
            context[f"can_{action}"] = self.request.user.has_perm(
                f"{options.app_label}.{action}_{options.model_name}"
            )
        context["permission_controlled"] = True
        return context


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


class EstacionamientoListView(AccesoEstacionamientosMixin, ListView):
    """Lista cajones para usuarios con permiso de lectura."""
    model = Estacionamiento
    permission_required = "estacionamientos.view_estacionamiento"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Estacionamientos",
        "create_url": "estacionamientos:estacionamiento_create",
        "update_url": "estacionamientos:estacionamiento_update",
        "delete_url": "estacionamientos:estacionamiento_delete",
    }


class EstacionamientoCreateView(AccesoEstacionamientosMixin, CreateView):
    """Crea cajones con el permiso de alta del modelo."""
    model = Estacionamiento
    permission_required = "estacionamientos.add_estacionamiento"
    form_class = EstacionamientoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "Crear estacionamiento"}


class EstacionamientoUpdateView(AccesoEstacionamientosMixin, UpdateView):
    """Edita cajones con el permiso de cambio del modelo."""
    model = Estacionamiento
    permission_required = "estacionamientos.change_estacionamiento"
    form_class = EstacionamientoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "Editar estacionamiento"}


class EstacionamientoDeleteView(AccesoEstacionamientosMixin, EliminacionProtegidaView):
    """Elimina cajones con el permiso de borrado del modelo."""
    model = Estacionamiento
    permission_required = "estacionamientos.delete_estacionamiento"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "estacionamiento"}


class SensorListView(AccesoEstacionamientosMixin, ListView):
    """Lista sensores para usuarios con permiso de lectura."""
    model = Sensor
    permission_required = "estacionamientos.view_sensor"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Sensores",
        "create_url": "estacionamientos:sensor_create",
        "update_url": "estacionamientos:sensor_update",
        "delete_url": "estacionamientos:sensor_delete",
    }


class SensorCreateView(AccesoEstacionamientosMixin, CreateView):
    """Crea sensores con el permiso de alta del modelo."""
    model = Sensor
    permission_required = "estacionamientos.add_sensor"
    form_class = SensorForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "Crear sensor"}


class SensorUpdateView(AccesoEstacionamientosMixin, UpdateView):
    """Edita sensores con el permiso de cambio del modelo."""
    model = Sensor
    permission_required = "estacionamientos.change_sensor"
    form_class = SensorForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "Editar sensor"}


class SensorDeleteView(AccesoEstacionamientosMixin, EliminacionProtegidaView):
    """Elimina sensores con el permiso de borrado del modelo."""
    model = Sensor
    permission_required = "estacionamientos.delete_sensor"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "sensor"}