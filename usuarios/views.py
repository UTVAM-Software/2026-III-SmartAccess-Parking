from django.contrib import messages
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import UsuarioForm, VehiculoForm
from .models import Usuario, Vehiculo


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


class UsuarioListView(ListView):
    model = Usuario
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Usuarios",
        "create_url": "usuarios:usuario_create",
        "update_url": "usuarios:usuario_update",
        "delete_url": "usuarios:usuario_delete",
    }


class UsuarioCreateView(CreateView):
    model = Usuario
    form_class = UsuarioForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "Crear usuario"}


class UsuarioUpdateView(UpdateView):
    model = Usuario
    form_class = UsuarioForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "Editar usuario"}


class UsuarioDeleteView(EliminacionProtegidaView):
    model = Usuario
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "usuario"}


class VehiculoListView(ListView):
    model = Vehiculo
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Vehículos",
        "create_url": "usuarios:vehiculo_create",
        "update_url": "usuarios:vehiculo_update",
        "delete_url": "usuarios:vehiculo_delete",
    }


class VehiculoCreateView(CreateView):
    model = Vehiculo
    form_class = VehiculoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "Crear vehículo"}


class VehiculoUpdateView(UpdateView):
    model = Vehiculo
    form_class = VehiculoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "Editar vehículo"}


class VehiculoDeleteView(EliminacionProtegidaView):
    model = Vehiculo
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "vehículo"}